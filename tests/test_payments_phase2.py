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
from app.models.payment import PaymentMode
from app.models.test import TestCategory, TestMaster
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestPaymentsPhase2(unittest.TestCase):
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
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        receptionist = User(
            email="rec@test.com",
            hashed_password=hash_password("RecPass123"),
            full_name="Receptionist User",
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )
        patient = Patient(
            uhid="HT-2026-00001",
            name="John Doe",
            gender=Gender.MALE,
            age_years=30,
            phone="9876543210",
            is_active=True,
        )
        category = TestCategory(name="Biochemistry")
        db.add_all([admin, receptionist, patient, category])
        db.commit()
        db.refresh(admin)
        db.refresh(receptionist)
        db.refresh(patient)
        db.refresh(category)

        test = TestMaster(
            category_id=category.id,
            test_code="LFT",
            name="Liver Function Test",
            price=Decimal("1000.00"),
            is_active=True,
        )
        db.add(test)
        db.commit()
        db.refresh(test)

        # Create Bill with ₹1000 payable amount
        bill = Bill(
            bill_number="BILL-2026-00001",
            patient_id=patient.id,
            created_by_id=receptionist.id,
            status=BillStatus.UNPAID,
            subtotal=Decimal("1000.00"),
            discount_type=DiscountType.NONE,
            payable_amount=Decimal("1000.00"),
            paid_amount=Decimal("0.00"),
            due_amount=Decimal("1000.00"),
            items=[
                BillItem(
                    test_id=test.id,
                    test_name="Liver Function Test",
                    test_code="LFT",
                    unit_price=Decimal("1000.00"),
                    quantity=1,
                    discount_amount=Decimal("0.00"),
                    line_total=Decimal("1000.00"),
                )
            ],
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)

        self.admin_id = admin.id
        self.rec_id = receptionist.id
        self.patient_id = patient.id
        self.bill_id = bill.id

        self.rec_token = create_access_token(str(self.rec_id))
        self.rec_headers = {"Authorization": f"Bearer {self.rec_token}"}
        db.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_01_partial_payment_and_due_recalculation(self):
        # 1. Pay ₹400 on a ₹1000 bill
        pay_payload = {
            "bill_id": self.bill_id,
            "amount": "400.00",
            "payment_mode": "UPI",
            "transaction_ref": "UPI-1234567890",
            "notes": "Advance payment",
        }
        res = self.client.post("/api/v1/payments", json=pay_payload, headers=self.rec_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        self.assertTrue(data["receipt_number"].startswith("RCP-2026-"))
        self.assertEqual(Decimal(str(data["amount"])), Decimal("400.00"))
        self.assertEqual(data["payment_mode"], "UPI")

        # 2. Check updated Bill status and due amount
        bill_res = self.client.get(f"/api/v1/bills/{self.bill_id}", headers=self.rec_headers)
        self.assertEqual(bill_res.status_code, 200)
        bill_data = bill_res.json()

        self.assertEqual(bill_data["status"], "PARTIALLY_PAID")
        self.assertEqual(Decimal(str(bill_data["paid_amount"])), Decimal("400.00"))
        self.assertEqual(Decimal(str(bill_data["due_amount"])), Decimal("600.00"))
        self.assertEqual(len(bill_data["payments"]), 1)

    def test_02_settle_remaining_balance_marks_bill_paid(self):
        # First payment: ₹400
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "400.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )

        # Second payment: Remaining ₹600 via CARD
        res2 = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "600.00", "payment_mode": "CARD", "transaction_ref": "TXN-CARD-99"},
            headers=self.rec_headers,
        )
        self.assertEqual(res2.status_code, 201)

        # Bill must now be fully PAID
        bill_res = self.client.get(f"/api/v1/bills/{self.bill_id}", headers=self.rec_headers)
        bill_data = bill_res.json()

        self.assertEqual(bill_data["status"], "PAID")
        self.assertEqual(Decimal(str(bill_data["paid_amount"])), Decimal("1000.00"))
        self.assertEqual(Decimal(str(bill_data["due_amount"])), Decimal("0.00"))
        self.assertEqual(len(bill_data["payments"]), 2)

    def test_03_overpayment_rejection(self):
        # Attempt to pay ₹1200 on ₹1000 bill -> Rejection
        res = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "1200.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("exceeds", res.json()["detail"].lower())

    def test_04_payment_on_fully_paid_bill_rejection(self):
        # Fully pay the bill
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "1000.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )

        # Subsequent payment attempt -> Rejection
        res = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "100.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("already fully paid", res.json()["detail"].lower())

    def test_05_invalid_amount_validations(self):
        # Zero amount rejected
        res_zero = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "0.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.assertEqual(res_zero.status_code, 422)

        # Negative amount rejected
        res_neg = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "-50.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.assertEqual(res_neg.status_code, 422)

    def test_06_unique_receipt_number_sequence(self):
        p1 = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "100.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        ).json()
        p2 = self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "100.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        ).json()

        r1 = p1["receipt_number"]
        r2 = p2["receipt_number"]
        self.assertNotEqual(r1, r2)
        seq1 = int(r1.split("-")[-1])
        seq2 = int(r2.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

    def test_07_list_payments_for_bill(self):
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "200.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": self.bill_id, "amount": "300.00", "payment_mode": "UPI"},
            headers=self.rec_headers,
        )

        res = self.client.get(f"/api/v1/payments/bill/{self.bill_id}", headers=self.rec_headers)
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 2)
        self.assertEqual(Decimal(str(items[0]["amount"])), Decimal("200.00"))
        self.assertEqual(Decimal(str(items[1]["amount"])), Decimal("300.00"))
