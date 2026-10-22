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
from app.models.doctor import Doctor
from app.models.patient import Gender, Patient, PatientType
from app.models.test_case import TestCase
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestBillingCorePhase1(unittest.TestCase):
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

        # Populate baseline users and data
        db = self.TestingSessionLocal()

        self.admin = User(
            email="admin@test.com",
            hashed_password=hash_password("AdminPass123"),
            full_name="Admin User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        self.receptionist = User(
            email="rec@test.com",
            hashed_password=hash_password("RecPass123"),
            full_name="Receptionist User",
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )
        self.doctor = Doctor(
            name="Dr. Gregory House",
            specialization="Diagnostics",
            phone="9988776655",
            is_active=True,
        )
        self.patient = Patient(
            uhid="HT-2026-00001",
            name="John Doe",
            gender=Gender.MALE,
            age_years=35,
            phone="9123456780",
            patient_type=PatientType.OPD,
            is_active=True,
        )

        db.add_all([self.admin, self.receptionist, self.doctor, self.patient])
        db.commit()
        db.refresh(self.admin)
        db.refresh(self.receptionist)
        db.refresh(self.doctor)
        db.refresh(self.patient)

        # Auth tokens
        self.admin_token = create_access_token(str(self.admin.id))
        self.rec_token = create_access_token(str(self.receptionist.id))

        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}
        self.rec_headers = {"Authorization": f"Bearer {self.rec_token}"}

        # Seed test cases
        self.cbc_test = TestCase(
            code="CBC",
            name="Complete Blood Count",
            price=Decimal("350.00"),
            is_active=True,
        )
        self.lft_test = TestCase(
            code="LFT",
            name="Liver Function Test",
            price=Decimal("750.00"),
            is_active=True,
        )
        self.inactive_test = TestCase(
            code="OLD_TEST",
            name="Obsolete Test",
            price=Decimal("200.00"),
            is_active=False,
        )
        db.add_all([self.cbc_test, self.lft_test, self.inactive_test])
        db.commit()
        db.refresh(self.cbc_test)
        db.refresh(self.lft_test)
        db.refresh(self.inactive_test)

        self.patient_id = self.patient.id
        self.doctor_id = self.doctor.id
        self.admin_id = self.admin.id
        self.rec_id = self.receptionist.id
        self.cbc_id = self.cbc_test.id
        self.lft_id = self.lft_test.id
        self.inactive_id = self.inactive_test.id
        db.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)

    def test_bill_creation_with_validations_and_math(self):
        # Bill with CBC (₹350) + LFT (₹750) = Subtotal ₹1100
        # Discount: 10% Flat or % -> Let's test 10% = ₹110 discount -> Payable = ₹990
        bill_data = {
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "items": [
                {"test_id": self.cbc_id, "quantity": 1, "discount_amount": "0.00"},
                {"test_id": self.lft_id, "quantity": 1, "discount_amount": "0.00"},
            ],
            "discount_type": "PERCENTAGE",
            "discount_value": "10.00",
            "discount_reason": "Senior Citizen Concession",
            "remarks": "Urgent reporting",
        }

        # Receptionist can create bill
        res = self.client.post("/api/v1/bills", json=bill_data, headers=self.rec_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        self.assertTrue(data["bill_number"].startswith("BILL-2026-"))
        self.assertEqual(Decimal(str(data["subtotal"])), Decimal("1100.00"))
        self.assertEqual(Decimal(str(data["discount_amount"])), Decimal("110.00"))
        self.assertEqual(Decimal(str(data["payable_amount"])), Decimal("990.00"))
        self.assertEqual(Decimal(str(data["paid_amount"])), Decimal("0.00"))
        self.assertEqual(Decimal(str(data["due_amount"])), Decimal("990.00"))
        self.assertEqual(data["status"], "UNPAID")
        self.assertEqual(len(data["items"]), 2)

    def test_bill_creation_rejects_inactive_test(self):
        bill_data = {
            "patient_id": self.patient_id,
            "items": [
                {"test_id": self.inactive_id, "quantity": 1},
            ],
        }
        res = self.client.post("/api/v1/bills", json=bill_data, headers=self.rec_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("inactive", res.json()["detail"].lower())

    def test_bill_creation_rejects_excessive_discount(self):
        # Bill with CBC (₹350), Flat discount ₹400 -> Should fail
        bill_data = {
            "patient_id": self.patient_id,
            "items": [
                {"test_id": self.cbc_id, "quantity": 1},
            ],
            "discount_type": "FLAT",
            "discount_value": "400.00",
        }
        res = self.client.post("/api/v1/bills", json=bill_data, headers=self.rec_headers)
        self.assertEqual(res.status_code, 400)
        self.assertIn("exceed", res.json()["detail"].lower())

    def test_historical_price_snapshot_immutability(self):
        # 1. Create a bill with CBC at initial price ₹350
        bill_data = {
            "patient_id": self.patient_id,
            "items": [
                {"test_id": self.cbc_id, "quantity": 1},
            ],
        }
        res = self.client.post("/api/v1/bills", json=bill_data, headers=self.rec_headers)
        self.assertEqual(res.status_code, 201)
        bill_id = res.json()["id"]

        # 2. Lab updates CBC price to ₹500 in master test catalog
        with self.TestingSessionLocal() as db:
            test = db.get(TestCase, self.cbc_id)
            test.price = Decimal("500.00")
            db.commit()

        # 3. Retrieve original bill - must remain ₹350
        get_res = self.client.get(f"/api/v1/bills/{bill_id}", headers=self.rec_headers)
        self.assertEqual(get_res.status_code, 200)
        bill_retrieved = get_res.json()

        self.assertEqual(Decimal(str(bill_retrieved["subtotal"])), Decimal("350.00"))
        self.assertEqual(Decimal(str(bill_retrieved["items"][0]["unit_price"])), Decimal("350.00"))
        self.assertEqual(Decimal(str(bill_retrieved["items"][0]["line_total"])), Decimal("350.00"))

    def test_sequential_bill_numbers(self):
        bill_1 = self.client.post(
            "/api/v1/bills",
            json={"patient_id": self.patient_id, "items": [{"test_id": self.cbc_id}]},
            headers=self.rec_headers,
        ).json()
        bill_2 = self.client.post(
            "/api/v1/bills",
            json={"patient_id": self.patient_id, "items": [{"test_id": self.cbc_id}]},
            headers=self.rec_headers,
        ).json()

        num1 = bill_1["bill_number"]
        num2 = bill_2["bill_number"]
        self.assertNotEqual(num1, num2)
        seq1 = int(num1.split("-")[-1])
        seq2 = int(num2.split("-")[-1])
        self.assertEqual(seq2, seq1 + 1)

