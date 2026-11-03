import unittest
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import create_access_token
from app.db.base import Base
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
from app.models.patient import Gender, Patient, PatientType
from app.models.test_case import TestCase
from app.models.test_parameter import TestParameter
from app.models.user import User, UserRole
from app.schemas.lab_order import (
    LabOrderCancelRequest,
    LabOrderCreate,
    LabResultBatchCreate,
    LabResultEntryItem,
    LabSampleCreate,
)
from app.services import lab_order_service

# SQLite In-memory setup
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class TestLabOrdersServiceWorkflow(unittest.TestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db = TestSession()

        # Seed Admin User
        self.admin = User(
            email="admin@hemotrack.com",
            hashed_password="fakehashadmin",
            full_name="System Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.db.add(self.admin)

        # Seed Patient
        self.patient = Patient(
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
        self.db.add(self.patient)

        # Seed Doctor
        self.doctor = Doctor(
            name="Dr. Suresh Rao",
            specialization="Pathologist",
            phone="9822334455",
            is_active=True,
        )
        self.db.add(self.doctor)

        # Seed Test Case
        self.test_case = TestCase(
            name="Complete Blood Count",
            code="CBC_TEST",
            sample_type="EDTA Whole Blood",
            price=Decimal("450.00"),
            is_active=True,
        )
        self.db.add(self.test_case)
        self.db.flush()

        # Seed Test Parameter
        self.param = TestParameter(
            test_case_id=self.test_case.id,
            name="Hemoglobin",
            code="HB",
            unit="g/dL",
            normal_range="13.0-17.0",
            critical_low="7.0",
            critical_high="20.0",
            is_required=True,
            display_order=1,
        )
        self.db.add(self.param)
        self.db.commit()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(bind=engine)

    def test_full_lab_order_lifecycle(self):
        # 1. Create Lab Order
        payload = LabOrderCreate(
            patient_id=self.patient.id,
            doctor_id=self.doctor.id,
            priority=OrderPriority.URGENT,
            clinical_notes="Suspected Anemia",
            test_case_ids=[self.test_case.id],
        )
        order = lab_order_service.create_lab_order(self.db, payload, self.admin.id)
        self.assertTrue(order.order_number.startswith("ORD-"))
        self.assertEqual(order.status, OrderStatus.PENDING)
        self.assertEqual(len(order.items), 1)
        self.assertEqual(len(order.samples), 1)

        sample = order.samples[0]
        order_item = order.items[0]

        # 2. Mark Sample Received in Lab
        rcv_sample = lab_order_service.receive_sample_in_lab(self.db, sample.id, self.admin.id)
        self.assertEqual(rcv_sample.status, SampleStatus.RECEIVED)
        self.assertEqual(order.status, OrderStatus.PROCESSING)

        # 3. Enter Results (Hemoglobin = 6.5 -> Critical Low)
        res_payload = LabResultBatchCreate(
            results=[
                LabResultEntryItem(
                    order_item_id=order_item.id,
                    parameter_id=self.param.id,
                    result_value="6.5",
                    comments="Critical value alert triggered",
                )
            ]
        )
        results = lab_order_service.enter_lab_results(self.db, order.id, res_payload, self.admin.id)
        self.assertEqual(len(results), 1)
        res = results[0]
        self.assertEqual(res.status, ResultStatus.UNDER_VERIFICATION)
        self.assertEqual(res.abnormality_flag, AbnormalityFlag.CRITICAL)

        # 4. Pathologist Verifies Result
        verified_res = lab_order_service.verify_lab_result(self.db, res.id, self.admin.id)
        self.assertEqual(verified_res.status, ResultStatus.VERIFIED)
        self.assertEqual(order_item.status, OrderItemStatus.VERIFIED)
        self.assertEqual(order.status, OrderStatus.COMPLETED)

        # 5. Generate Final Released Report
        report = lab_order_service.generate_final_report(
            self.db, order.id, "Urgent blood transfusion consultation needed", self.admin.id
        )
        self.assertTrue(report.report_number.startswith("REP-"))
        self.assertEqual(report.status, ReportStatus.RELEASED)
        self.assertIsNotNone(report.report_data_snapshot)

        # 6. Verify Dashboard KPIs
        stats = lab_order_service.get_lab_dashboard_stats(self.db)
        self.assertGreaterEqual(stats.total_orders, 1)
        self.assertGreaterEqual(stats.completed_orders, 1)

    def test_cancel_order(self):
        payload = LabOrderCreate(
            patient_id=self.patient.id,
            priority=OrderPriority.ROUTINE,
            test_case_ids=[self.test_case.id],
        )
        order = lab_order_service.create_lab_order(self.db, payload, self.admin.id)
        cancelled = lab_order_service.cancel_lab_order(
            self.db, order.id, "Patient requested registration refund", self.admin.id
        )
        self.assertTrue(cancelled.is_cancelled)
        self.assertEqual(cancelled.status, OrderStatus.CANCELLED)


if __name__ == "__main__":
    unittest.main()
