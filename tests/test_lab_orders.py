from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.db.base import Base
from app.main import app
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.lab_order import (
    AbnormalityFlag,
    LabOrder,
    LabOrderItem,
    LabReport,
    LabResult,
    LabSample,
    OrderItemStatus,
    OrderPriority,
    OrderStatus,
    ReportStatus,
    ResultStatus,
    SampleStatus,
)
from app.models.parameter_reference_range import ParameterReferenceRange
from app.models.patient import Gender, Patient, PatientType
from app.models.test_case import TestCase
from app.models.test_parameter import TestParameter
from app.models.user import User, UserRole
from app.core.security import create_access_token

# In-memory SQLite for isolated unit testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(db_session):
    admin = User(
        email="admin@hemotrack.com",
        hashed_password="fakehashadmin",
        full_name="System Admin",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db_session.add(admin)
    db_session.commit()
    db_session.refresh(admin)

    token = create_access_token(subject=admin.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_setup_data(db_session):
    # Patient
    patient = Patient(
        uhid="UHID-9999",
        name="Sunil Patil",
        gender=Gender.MALE,
        age_years=35,
        age_months=2,
        age_days=10,
        patient_type=PatientType.OPD,
        phone="9876543210",
        is_active=True,
    )
    db_session.add(patient)

    # Doctor
    doctor = Doctor(
        name="Dr. Suresh Rao",
        specialization="Pathologist",
        phone="9822334455",
        is_active=True,
    )
    db_session.add(doctor)

    # Test Case
    test_case = TestCase(
        name="Complete Blood Count",
        code="CBC_TEST",
        sample_type="EDTA Whole Blood",
        price=Decimal("450.00"),
        is_active=True,
    )
    db_session.add(test_case)
    db_session.flush()

    # Test Parameter
    param = TestParameter(
        test_case_id=test_case.id,
        name="Hemoglobin",
        code="HB",
        unit="g/dL",
        normal_range="13.0-17.0",
        critical_low="7.0",
        critical_high="20.0",
        is_required=True,
        display_order=1,
    )
    db_session.add(param)
    db_session.commit()

    return {
        "patient_id": patient.id,
        "doctor_id": doctor.id,
        "test_case_id": test_case.id,
        "parameter_id": param.id,
    }


def test_create_and_workflow_lab_order(client, auth_headers, test_setup_data):
    # 1. Create Order
    create_payload = {
        "patient_id": test_setup_data["patient_id"],
        "doctor_id": test_setup_data["doctor_id"],
        "priority": "URGENT",
        "clinical_notes": "Suspected Anemia",
        "test_case_ids": [test_setup_data["test_case_id"]],
    }
    resp = client.post("/api/v1/lab-orders", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    order_data = resp.json()
    order_id = order_data["id"]
    assert order_data["order_number"].startswith("ORD-")
    assert order_data["status"] == "PENDING"
    assert len(order_data["items"]) == 1
    assert len(order_data["samples"]) == 1
    sample_id = order_data["samples"][0]["id"]
    order_item_id = order_data["items"][0]["id"]

    # 2. Receive Sample in Lab
    resp_rcv = client.patch(f"/api/v1/lab-orders/samples/{sample_id}/receive", headers=auth_headers)
    assert resp_rcv.status_code == 200
    assert resp_rcv.json()["status"] == "RECEIVED"

    # 3. Enter Results
    result_payload = {
        "results": [
            {
                "order_item_id": order_item_id,
                "parameter_id": test_setup_data["parameter_id"],
                "result_value": "10.5",  # Below 13.0, expected LOW
                "comments": "Mild anemia flagged",
            }
        ]
    }
    resp_res = client.post(f"/api/v1/lab-orders/{order_id}/results", json=result_payload, headers=auth_headers)
    assert resp_res.status_code == 201
    results = resp_res.json()
    assert len(results) == 1
    result_id = results[0]["id"]
    assert results[0]["status"] == "UNDER_VERIFICATION"

    # 4. Verify Result
    resp_vfy = client.post(f"/api/v1/lab-orders/results/{result_id}/verify", headers=auth_headers)
    assert resp_vfy.status_code == 200
    assert resp_vfy.json()["status"] == "VERIFIED"

    # 5. Generate Final Report
    report_payload = {"summary_notes": "Doctor advised Iron Supplements"}
    resp_rep = client.post(f"/api/v1/lab-orders/{order_id}/reports", json=report_payload, headers=auth_headers)
    assert resp_rep.status_code == 201
    report = resp_rep.json()
    assert report["report_number"].startswith("REP-")
    assert report["status"] == "RELEASED"

    # 6. Verify Dashboard KPIs
    resp_dash = client.get("/api/v1/lab-orders/dashboard/stats", headers=auth_headers)
    assert resp_dash.status_code == 200
    stats = resp_dash.json()
    assert stats["total_orders"] >= 1
    assert stats["completed_orders"] >= 1


def test_order_cancellation(client, auth_headers, test_setup_data):
    create_payload = {
        "patient_id": test_setup_data["patient_id"],
        "priority": "ROUTINE",
        "test_case_ids": [test_setup_data["test_case_id"]],
    }
    resp = client.post("/api/v1/lab-orders", json=create_payload, headers=auth_headers)
    assert resp.status_code == 201
    order_id = resp.json()["id"]

    # Cancel
    cancel_payload = {"reason": "Patient requested discharge without tests"}
    resp_cancel = client.post(f"/api/v1/lab-orders/{order_id}/cancel", json=cancel_payload, headers=auth_headers)
    assert resp_cancel.status_code == 200
    cancelled_order = resp_cancel.json()
    assert cancelled_order["is_cancelled"] is True
    assert cancelled_order["status"] == "CANCELLED"
