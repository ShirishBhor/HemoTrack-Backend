from datetime import datetime
from decimal import Decimal
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import create_access_token, hash_password
from app.db import Base
from app.main import app
from app.models.bill import Bill, BillItem, BillStatus, DiscountType
from app.models.doctor import Doctor
from app.models.patient import Gender, Patient, PatientType
from app.models.test import TestCategory, TestMaster
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestReceiptAndCancellationPhase3(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        def override_get_db():
            db = self.TestingSessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(app)

        db = self.TestingSessionLocal()
        admin = User(
            email="admin@test.com",
            hashed_password=hash_password("AdminPass123"),
            full_name="Admin Director",
            role=UserRole.ADMIN,
            is_active=True,
        )
        manager = User(
            email="manager@test.com",
            hashed_password=hash_password("ManagerPass123"),
            full_name="Lab Manager",
            role=UserRole.LAB_MANAGER,
            is_active=True,
        )
        receptionist = User(
            email="rec@test.com",
            hashed_password=hash_password("RecPass123"),
            full_name="Front Desk Clerk",
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )
        doctor = Doctor(
            name="Dr. Gregory House",
            specialization="Diagnostics",
            phone="9876543210",
            is_active=True,
        )
        patient = Patient(
            uhid="HT-2026-00001",
            name="Alice Smith",
            gender=Gender.FEMALE,
            age_years=28,
            phone="9123456780",
            address="42 Elm Street, Metropolis",
            patient_type=PatientType.OPD,
            is_active=True,
        )
        category = TestCategory(name="Biochemistry")
        db.add_all([admin, manager, receptionist, doctor, patient, category])
        db.commit()
        db.refresh(admin)
        db.refresh(manager)
        db.refresh(receptionist)
        db.refresh(doctor)
        db.refresh(patient)
        db.refresh(category)

        test = TestMaster(
            category_id=category.id,
            test_code="CBC",
            name="Complete Blood Count",
            price=Decimal("500.00"),
            is_active=True,
        )
        db.add(test)
        db.commit()
        db.refresh(test)

        # Create Bill with ₹500
        bill = Bill(
            bill_number="BILL-2026-00001",
            patient_id=patient.id,
            doctor_id=doctor.id,
            created_by_id=receptionist.id,
            status=BillStatus.UNPAID,
            subtotal=Decimal("500.00"),
            discount_type=DiscountType.NONE,
            payable_amount=Decimal("500.00"),
            paid_amount=Decimal("0.00"),
            due_amount=Decimal("500.00"),
            items=[
                BillItem(
                    test_id=test.id,
                    test_name="Complete Blood Count",
                    test_code="CBC",
                    unit_price=Decimal("500.00"),
                    quantity=1,
                    discount_amount=Decimal("0.00"),
                    line_total=Decimal("500.00"),
                )
            ],
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        self.admin_id = admin.id
        self.manager_id = manager.id
        self.rec_id = receptionist.id
        self.patient_id = patient.id
        self.doctor_id = doctor.id
        self.bill_id = bill.id

        self.admin_token = create_access_token(str(self.admin_id))
        self.manager_token = create_access_token(str(self.manager_id))
        self.rec_token = create_access_token(str(self.rec_id))

        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.manager_headers = {"Authorization": f"Bearer {self.manager_token}"}
        self.rec_headers = {"Authorization": f"Bearer {self.rec_token}"}
        db.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_01_printable_receipt_data_payload(self):
        # Add a partial payment
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "200.00", "payment_mode": "UPI", "transaction_ref": "UPI-REC-1"},
            headers=self.rec_headers,
        )

        res = self.client.get(f"/api/v1/bills/{self.bill_id}/receipt", headers=self.rec_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Lab header details
        self.assertIn("lab_header", data)
        self.assertEqual(data["lab_header"]["lab_name"], "HemoTrack Diagnostic Center")

        # Patient & Doctor details
        self.assertEqual(data["patient"]["name"], "Alice Smith")
        self.assertEqual(data["patient"]["uhid"], "HT-2026-00001")
        self.assertEqual(data["doctor"]["name"], "Dr. Gregory House")
        self.assertEqual(data["billed_by_name"], "Front Desk Clerk")

        # Financial breakdown
        self.assertEqual(data["bill_number"], "BILL-2026-00001")
        self.assertEqual(Decimal(str(data["subtotal"])), Decimal("500.00"))
        self.assertEqual(Decimal(str(data["payable_amount"])), Decimal("500.00"))
        self.assertEqual(Decimal(str(data["paid_amount"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(data["due_amount"])), Decimal("300.00"))
        self.assertEqual(data["status"], "PARTIALLY_PAID")

        # Items & Payments ledger
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["test_code"], "CBC")
        self.assertEqual(len(data["payments"]), 1)
        self.assertEqual(data["payments"][0]["payment_mode"], "UPI")
        self.assertEqual(data["payments"][0]["received_by_name"], "Front Desk Clerk")

    def test_02_cancellation_rbac_permissions(self):
        # 1. Receptionist CANNOT cancel a bill (Requires ADMIN or LAB_MANAGER)
        payload = {"reason": "Patient requested cancellation"}
        rec_res = self.client.post(f"/api/v1/bills/{self.bill_id}/cancel", json=payload, headers=self.rec_headers)
        self.assertEqual(rec_res.status_code, 403)

        # 2. Lab Manager CAN cancel a bill
        mgr_res = self.client.post(f"/api/v1/bills/{self.bill_id}/cancel", json=payload, headers=self.manager_headers)
        self.assertEqual(mgr_res.status_code, 200)
        mgr_data = mgr_res.json()
        self.assertTrue(mgr_data["is_cancelled"])
        self.assertEqual(mgr_data["status"], "CANCELLED")
        self.assertEqual(mgr_data["cancellation_reason"], "Patient requested cancellation")

    def test_03_cancellation_requires_valid_reason(self):
        # Blank / too short reason fails schema validation
        res = self.client.post(f"/api/v1/bills/{self.bill_id}/cancel", json={"reason": "  "}, headers=self.admin_headers)
        self.assertEqual(res.status_code, 422)

    def test_04_repeat_cancellation_rejection(self):
        # First cancellation
        self.client.post(
            f"/api/v1/bills/{self.bill_id}/cancel",
            json={"reason": "Test duplicate order"},
            headers=self.admin_headers,
        )

        # Second cancellation attempt
        res2 = self.client.post(
            f"/api/v1/bills/{self.bill_id}/cancel",
            json={"reason": "Cancelled again"},
            headers=self.admin_headers,
        )
        self.assertEqual(res2.status_code, 400)
        self.assertIn("already been cancelled", res2.json()["detail"].lower())

    def test_05_cancelled_bill_with_payments_preserves_records_and_blocks_new_payments(self):
        # 1. Collect partial payment ₹250
        pay_res = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "250.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.assertEqual(pay_res.status_code, 201)

        # 2. Cancel bill by Admin
        cancel_res = self.client.post(
            f"/api/v1/bills/{self.bill_id}/cancel",
            json={"reason": "Patient withdrew sample"},
            headers=self.admin_headers,
        )
        self.assertEqual(cancel_res.status_code, 200)

        # 3. Verify bill details: items and payment history are PRESERVED
        get_res = self.client.get(f"/api/v1/bills/{self.bill_id}", headers=self.rec_headers)
        bill = get_res.json()
        self.assertTrue(bill["is_cancelled"])
        self.assertEqual(bill["status"], "CANCELLED")
        self.assertEqual(len(bill["items"]), 1)
        self.assertEqual(len(bill["payments"]), 1)
        self.assertEqual(Decimal(str(bill["paid_amount"])), Decimal("250.00"))

        # 4. Attempting new payment on cancelled bill is strictly REJECTED
        new_pay_res = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "100.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.assertEqual(new_pay_res.status_code, 400)
        self.assertIn("cancelled", new_pay_res.json()["detail"].lower())
