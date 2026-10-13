import os
import unittest
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base  # Automatically imports models via app.db
from app.core.deps import get_db
from app.main import app
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestUserEnhancementsPhase1(unittest.TestCase):
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

        # Create Admin User
        db = self.TestingSessionLocal()
        from app.core.security import hash_password

        admin = User(
            email="admin@test.com",
            hashed_password=hash_password("AdminPass123"),
            full_name="Test Admin",
            role=UserRole.ADMIN,
            is_active=True,
            employee_code="EMP-ADMIN",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        self.admin_id = admin.id
        db.close()

        # Login as Admin to get Token
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

    def test_01_create_user_with_employee_code_and_department(self):
        payload = {
            "email": "staff1@test.com",
            "password": "Password123",
            "full_name": "Staff One",
            "role": "receptionist",
            "employee_code": " emp-1001 ",
            "department": " Front Desk ",
            "profile_picture_url": "https://example.com/avatar.png",
        }
        res = self.client.post("/api/v1/users", json=payload, headers=self.auth_headers)
        self.assertEqual(res.status_code, 201)
        data = res.json()
        self.assertEqual(data["employee_code"], "EMP-1001")
        self.assertEqual(data["department"], "Front Desk")
        self.assertEqual(data["profile_picture_url"], "https://example.com/avatar.png")
        self.assertEqual(data["failed_login_attempts"], 0)
        self.assertFalse(data["is_locked"])
        self.assertIsNone(data["last_login_at"])

    def test_02_duplicate_employee_code_rejection(self):
        payload1 = {
            "email": "user1@test.com",
            "password": "Password123",
            "full_name": "User One",
            "employee_code": "EMP-2000",
        }
        res1 = self.client.post("/api/v1/users", json=payload1, headers=self.auth_headers)
        self.assertEqual(res1.status_code, 201)

        payload2 = {
            "email": "user2@test.com",
            "password": "Password123",
            "full_name": "User Two",
            "employee_code": "emp-2000",
        }
        res2 = self.client.post("/api/v1/users", json=payload2, headers=self.auth_headers)
        self.assertEqual(res2.status_code, 400)
        self.assertIn("Employee code already registered", res2.json()["detail"])

    def test_03_successful_login_updates_last_login_at_and_resets_failures(self):
        payload = {
            "email": "loginuser@test.com",
            "password": "CorrectPassword123",
            "full_name": "Login User",
        }
        self.client.post("/api/v1/users", json=payload, headers=self.auth_headers)

        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "loginuser@test.com", "password": "CorrectPassword123"},
        )
        self.assertEqual(login_res.status_code, 200)

        token = login_res.json()["access_token"]
        me_res = self.client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        self.assertEqual(me_res.status_code, 200)
        data = me_res.json()
        self.assertIsNotNone(data["last_login_at"])
        self.assertEqual(data["failed_login_attempts"], 0)
        self.assertFalse(data["is_locked"])

    def test_04_failed_login_attempts_and_account_lockout(self):
        payload = {
            "email": "victim@test.com",
            "password": "CorrectPassword123",
            "full_name": "Victim User",
        }
        create_res = self.client.post("/api/v1/users", json=payload, headers=self.auth_headers)
        user_id = create_res.json()["id"]

        for _ in range(4):
            res = self.client.post(
                "/api/v1/auth/login",
                json={"email": "victim@test.com", "password": "WrongPassword"},
            )
            self.assertEqual(res.status_code, 401)

        user_res = self.client.get(f"/api/v1/users/{user_id}", headers=self.auth_headers)
        self.assertEqual(user_res.json()["failed_login_attempts"], 4)
        self.assertFalse(user_res.json()["is_locked"])

        res5 = self.client.post(
            "/api/v1/auth/login",
            json={"email": "victim@test.com", "password": "WrongPassword"},
        )
        self.assertEqual(res5.status_code, 403)
        self.assertIn("locked", res5.json()["detail"])

        user_res = self.client.get(f"/api/v1/users/{user_id}", headers=self.auth_headers)
        self.assertTrue(user_res.json()["is_locked"])
        self.assertEqual(user_res.json()["failed_login_attempts"], 5)

        locked_login_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "victim@test.com", "password": "CorrectPassword123"},
        )
        self.assertEqual(locked_login_res.status_code, 403)
        self.assertIn("locked", locked_login_res.json()["detail"])

    def test_05_admin_unlock_endpoint(self):
        payload = {
            "email": "lockeduser@test.com",
            "password": "Password123",
            "full_name": "Locked User",
        }
        create_res = self.client.post("/api/v1/users", json=payload, headers=self.auth_headers)
        user_id = create_res.json()["id"]

        for _ in range(5):
            self.client.post(
                "/api/v1/auth/login",
                json={"email": "lockeduser@test.com", "password": "BadPassword"},
            )

        user_res = self.client.get(f"/api/v1/users/{user_id}", headers=self.auth_headers)
        self.assertTrue(user_res.json()["is_locked"])

        unlock_res = self.client.post(f"/api/v1/users/{user_id}/unlock", headers=self.auth_headers)
        self.assertEqual(unlock_res.status_code, 200)
        self.assertFalse(unlock_res.json()["is_locked"])
        self.assertEqual(unlock_res.json()["failed_login_attempts"], 0)

        login_res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "lockeduser@test.com", "password": "Password123"},
        )
        self.assertEqual(login_res.status_code, 200)

    def test_06_user_deactivation_and_self_deactivation_prevention(self):
        payload = {
            "email": "deactivate_me@test.com",
            "password": "Password123",
            "full_name": "Target User",
        }
        create_res = self.client.post("/api/v1/users", json=payload, headers=self.auth_headers)
        user_id = create_res.json()["id"]

        deact_res = self.client.delete(f"/api/v1/users/{user_id}", headers=self.auth_headers)
        self.assertEqual(deact_res.status_code, 200)
        self.assertFalse(deact_res.json()["is_active"])

        self_deact_res = self.client.delete(f"/api/v1/users/{self.admin_id}", headers=self.auth_headers)
        self.assertEqual(self_deact_res.status_code, 400)
        self.assertIn("cannot deactivate their own account", self_deact_res.json()["detail"])


if __name__ == "__main__":
    unittest.main()
