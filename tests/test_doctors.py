import unittest
from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import hash_password
from app.db import Base
from app.main import app
from app.models.doctor import Doctor
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestDoctorEnhancements(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            SQLALCHEMY_DATABASE_URL,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        self.TestingSessionLocal = sessionmaker(
            autocommit=False, autoflush=False, bind=self.engine
        )
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
        tech = User(
            email="tech@test.com",
            hashed_password=hash_password("TechPass123"),
            full_name="Lab Technician",
            role=UserRole.LAB_TECHNICIAN,
            is_active=True,
        )
        db.add_all([admin, tech])
        db.commit()

        # Login as admin
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123"},
        )
        self.assertEqual(res.status_code, 200)
        self.admin_token = res.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Login as technician (read-only for doctor mutations)
        res_tech = self.client.post(
            "/api/v1/auth/login",
            json={"email": "tech@test.com", "password": "TechPass123"},
        )
        self.assertEqual(res_tech.status_code, 200)
        self.tech_token = res_tech.json()["access_token"]
        self.tech_headers = {"Authorization": f"Bearer {self.tech_token}"}
        db.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_create_and_get_doctor(self):
        payload = {
            "name": "Dr. Rajesh Sharma",
            "specialization": "Cardiology",
            "phone": "9876543210",
            "email": "rajesh.sharma@example.com",
            "clinic_address": "MG Road, Pune",
        }
        res = self.client.post("/api/v1/doctors", json=payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["name"], "Dr. Rajesh Sharma")
        self.assertEqual(data["phone"], "9876543210")
        self.assertTrue(data["is_active"])
        doctor_id = data["id"]

        # Fetch by ID
        get_res = self.client.get(f"/api/v1/doctors/{doctor_id}", headers=self.admin_headers)
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.json()["id"], doctor_id)

    def test_phone_validation_indian_mobile(self):
        # Invalid phone: starts with 5 (not 6-9) or wrong length
        payload = {
            "name": "Dr. Invalid Phone",
            "phone": "5876543210",
        }
        res = self.client.post("/api/v1/doctors", json=payload, headers=self.admin_headers)
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        payload["phone"] = "98765"
        res2 = self.client.post("/api/v1/doctors", json=payload, headers=self.admin_headers)
        self.assertEqual(res2.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_duplicate_email_or_phone_conflict(self):
        payload = {
            "name": "Dr. First",
            "phone": "9822012345",
            "email": "first@example.com",
        }
        res1 = self.client.post("/api/v1/doctors", json=payload, headers=self.admin_headers)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Duplicate phone
        dup_phone = {
            "name": "Dr. Second",
            "phone": "9822012345",
        }
        res2 = self.client.post("/api/v1/doctors", json=dup_phone, headers=self.admin_headers)
        self.assertEqual(res2.status_code, status.HTTP_409_CONFLICT)

        # Duplicate email
        dup_email = {
            "name": "Dr. Third",
            "email": "first@example.com",
        }
        res3 = self.client.post("/api/v1/doctors", json=dup_email, headers=self.admin_headers)
        self.assertEqual(res3.status_code, status.HTTP_409_CONFLICT)

    def test_list_and_search_doctors(self):
        # Create doctors
        self.client.post(
            "/api/v1/doctors",
            json={"name": "Dr. Amit Patel", "specialization": "Pathology", "phone": "9811111111"},
            headers=self.admin_headers,
        )
        self.client.post(
            "/api/v1/doctors",
            json={"name": "Dr. Sneha Kulkarni", "specialization": "Neurology", "phone": "9822222222"},
            headers=self.admin_headers,
        )

        # List all
        res = self.client.get("/api/v1/doctors", headers=self.admin_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        body = res.json()
        self.assertIn("total", body)
        self.assertIn("items", body)
        self.assertEqual(body["total"], 2)
        self.assertEqual(len(body["items"]), 2)

        # Search by specialization
        search_res = self.client.get("/api/v1/doctors?search=pathology", headers=self.admin_headers)
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        search_body = search_res.json()
        self.assertEqual(search_body["total"], 1)
        self.assertEqual(search_body["items"][0]["name"], "Dr. Amit Patel")

    def test_update_doctor_patch(self):
        res = self.client.post(
            "/api/v1/doctors",
            json={"name": "Dr. Original", "phone": "9933333333"},
            headers=self.admin_headers,
        )
        doc_id = res.json()["id"]

        # Partial update
        patch_res = self.client.patch(
            f"/api/v1/doctors/{doc_id}",
            json={"specialization": "Oncology"},
            headers=self.admin_headers,
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.json()["specialization"], "Oncology")
        self.assertEqual(patch_res.json()["name"], "Dr. Original")

        # Empty payload rejected
        empty_res = self.client.patch(
            f"/api/v1/doctors/{doc_id}",
            json={},
            headers=self.admin_headers,
        )
        self.assertEqual(empty_res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_deactivate_and_reactivate_doctor(self):
        res = self.client.post(
            "/api/v1/doctors",
            json={"name": "Dr. Active", "phone": "9844444444"},
            headers=self.admin_headers,
        )
        doc_id = res.json()["id"]

        # Deactivate
        deact_res = self.client.patch(
            f"/api/v1/doctors/{doc_id}/status", json={"is_active": False}, headers=self.admin_headers
        )
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)
        self.assertFalse(deact_res.json()["is_active"])

        # Second deactivate should return 400
        deact_again = self.client.patch(
            f"/api/v1/doctors/{doc_id}/status", json={"is_active": False}, headers=self.admin_headers
        )
        self.assertEqual(deact_again.status_code, status.HTTP_400_BAD_REQUEST)

        # Active only listing excludes deactivated doctor
        list_res = self.client.get("/api/v1/doctors?is_active=true", headers=self.admin_headers)
        self.assertEqual(list_res.json()["total"], 0)

        # Reactivate
        react_res = self.client.patch(
            f"/api/v1/doctors/{doc_id}/status", json={"is_active": True}, headers=self.admin_headers
        )
        self.assertEqual(react_res.status_code, status.HTTP_200_OK)
        self.assertTrue(react_res.json()["is_active"])
