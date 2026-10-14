import unittest
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.db import Base
from app.main import app
from app.models.doctor import Doctor
from app.models.patient import BloodGroup, Gender, MaritalStatus, Patient, PatientType
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestPatientEnhancementsPhase2(unittest.TestCase):
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

        # Setup Admin User & Doctor
        db = self.TestingSessionLocal()
        from app.core.security import hash_password

        admin = User(
            email="admin@test.com",
            hashed_password=hash_password("AdminPass123"),
            full_name="Test Admin",
            role=UserRole.ADMIN,
            is_active=True,
        )
        doctor = Doctor(
            name="Dr. Smith",
            specialization="Hematology",
            phone="9876543210",
            is_active=True,
        )
        db.add_all([admin, doctor])
        db.commit()
        db.refresh(admin)
        db.refresh(doctor)

        self.admin_id = admin.id
        self.doctor_id = doctor.id
        db.close()

        # Login to get token
        response = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123"},
        )
        self.assertEqual(response.status_code, 200)
        self.admin_token = response.json()["access_token"]
        self.auth_headers = {"Authorization": f"Bearer {self.admin_token}"}

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_01_auto_uhid_generation_and_relationships(self):
        payload = {
            "name": "John Doe",
            "gender": "male",
            "patient_type": "OPD",
            "phone": "9998887770",
            "email": "johndoe@test.com",
            "referred_by_doctor_id": self.doctor_id,
        }
        res = self.client.post("/api/v1/patients", json=payload, headers=self.auth_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        # Verify UHID auto-generation
        current_year = date.today().year
        self.assertTrue(data["uhid"].startswith(f"HT-{current_year}-"))
        self.assertEqual(data["blood_group"], "UNKNOWN")

        # Verify Doctor & User relationships
        self.assertEqual(data["created_by"], self.admin_id)
        self.assertIsNotNone(data["referred_by_doctor"])
        self.assertEqual(data["referred_by_doctor"]["name"], "Dr. Smith")

    def test_02_dob_age_auto_calculation_and_future_dob_rejection(self):
        dob_10yr = date.today().replace(year=date.today().year - 10)
        payload = {
            "name": "Child Patient",
            "gender": "female",
            "dob": dob_10yr.isoformat(),
            "blood_group": "A+",
            "guardian_name": "Parent Patient",
            "emergency_contact_phone": "1112223334",
        }
        res = self.client.post("/api/v1/patients", json=payload, headers=self.auth_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["age_years"], 10)
        self.assertEqual(data["blood_group"], "A+")
        self.assertEqual(data["guardian_name"], "Parent Patient")

        future_dob = date.today() + timedelta(days=1)
        bad_payload = {
            "name": "Future Baby",
            "gender": "male",
            "dob": future_dob.isoformat(),
        }
        res_bad = self.client.post("/api/v1/patients", json=bad_payload, headers=self.auth_headers)
        self.assertEqual(res_bad.status_code, 422)

    def test_03_date_sequence_validation(self):
        today = date.today()
        yesterday = today - timedelta(days=1)

        bad_sequence = {
            "name": "Date Test",
            "gender": "male",
            "collection_date": today.isoformat(),
            "received_date": yesterday.isoformat(),
        }
        res = self.client.post("/api/v1/patients", json=bad_sequence, headers=self.auth_headers)
        self.assertEqual(res.status_code, 422)

        valid_sequence = {
            "name": "Date Test Valid",
            "gender": "male",
            "collection_date": yesterday.isoformat(),
            "received_date": today.isoformat(),
            "reporting_date": today.isoformat(),
        }
        res_valid = self.client.post("/api/v1/patients", json=valid_sequence, headers=self.auth_headers)
        self.assertEqual(res_valid.status_code, 201)

    def test_04_sample_barcode_and_uhid_lookup_apis(self):
        payload = {
            "name": "Barcode Patient",
            "gender": "female",
            "national_id": "NAT-998877",
            "sample_barcode": "BC-12345678",
            "marital_status": "MARRIED",
        }
        create_res = self.client.post("/api/v1/patients", json=payload, headers=self.auth_headers)
        self.assertEqual(create_res.status_code, 201)
        data = create_res.json()
        uhid = data["uhid"]

        uhid_res = self.client.get(f"/api/v1/patients/uhid/{uhid}", headers=self.auth_headers)
        self.assertEqual(uhid_res.status_code, 200)
        self.assertEqual(uhid_res.json()["name"], "Barcode Patient")

        barcode_res = self.client.get("/api/v1/patients/barcode/BC-12345678", headers=self.auth_headers)
        self.assertEqual(barcode_res.status_code, 200)
        self.assertEqual(barcode_res.json()["national_id"], "NAT-998877")

    def test_05_multi_field_patient_search(self):
        payload = {
            "name": "Alice Wonderland",
            "gender": "female",
            "phone": "5554443332",
            "email": "alice@wonderland.com",
            "national_id": "ID-ALICE-100",
            "sample_barcode": "BC-ALICE-200",
        }
        self.client.post("/api/v1/patients", json=payload, headers=self.auth_headers)

        res1 = self.client.get("/api/v1/patients?search=wonderland", headers=self.auth_headers)
        self.assertEqual(len(res1.json()), 1)

        res2 = self.client.get("/api/v1/patients?search=5554443332", headers=self.auth_headers)
        self.assertEqual(len(res2.json()), 1)

        res3 = self.client.get("/api/v1/patients?search=ID-ALICE-100", headers=self.auth_headers)
        self.assertEqual(len(res3.json()), 1)

        res4 = self.client.get("/api/v1/patients?search=BC-ALICE-200", headers=self.auth_headers)
        self.assertEqual(len(res4.json()), 1)


if __name__ == "__main__":
    unittest.main()
