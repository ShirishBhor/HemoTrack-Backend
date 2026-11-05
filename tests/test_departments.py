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
from app.models.department import Department
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestDepartmentAPIs(unittest.TestCase):
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
            email="admin_dept@test.com",
            hashed_password=hash_password("AdminPass123"),
            full_name="Admin Dept User",
            role=UserRole.ADMIN,
            is_active=True,
        )
        tech = User(
            email="tech_dept@test.com",
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
            json={"email": "admin_dept@test.com", "password": "AdminPass123"},
        )
        self.assertEqual(res.status_code, 200)
        self.admin_token = res.json()["access_token"]
        self.admin_headers = {"Authorization": f"Bearer {self.admin_token}"}

        # Login as tech
        res = self.client.post(
            "/api/v1/auth/login",
            json={"email": "tech_dept@test.com", "password": "TechPass123"},
        )
        self.assertEqual(res.status_code, 200)
        self.tech_token = res.json()["access_token"]
        self.tech_headers = {"Authorization": f"Bearer {self.tech_token}"}
        db.close()

    def tearDown(self):
        Base.metadata.drop_all(bind=self.engine)

    def test_01_create_department(self):
        res = self.client.post(
            "/api/v1/departments",
            json={
                "name": "Biochemistry",
                "code": "BIO-01",
                "description": "Biochemistry and clinical chemistry department",
            },
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["name"], "Biochemistry")
        self.assertEqual(data["code"], "BIO-01")
        self.assertTrue(data["is_active"])
        self.assertIn("id", data)

    def test_02_create_department_duplicate_error(self):
        self.client.post(
            "/api/v1/departments",
            json={"name": "Hematology", "code": "HEM-01"},
            headers=self.admin_headers,
        )
        res = self.client.post(
            "/api/v1/departments",
            json={"name": "Hematology", "code": "HEM-01"},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

    def test_03_create_department_permission_denied_for_tech(self):
        res = self.client.post(
            "/api/v1/departments",
            json={"name": "Microbiology", "code": "MIC-01"},
            headers=self.tech_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_04_list_and_search_departments(self):
        self.client.post(
            "/api/v1/departments",
            json={"name": "Clinical Pathology", "code": "CP-01"},
            headers=self.admin_headers,
        )
        self.client.post(
            "/api/v1/departments",
            json={"name": "Immunology", "code": "IMM-01"},
            headers=self.admin_headers,
        )

        res = self.client.get("/api/v1/departments", headers=self.tech_headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        items = res.json()
        self.assertEqual(len(items), 2)

        res_search = self.client.get(
            "/api/v1/departments/search?q=Immuno", headers=self.tech_headers
        )
        self.assertEqual(res_search.status_code, status.HTTP_200_OK)
        search_items = res_search.json()
        self.assertEqual(len(search_items), 1)
        self.assertEqual(search_items[0]["name"], "Immunology")

    def test_05_update_and_deactivate_reactivate_department(self):
        create_res = self.client.post(
            "/api/v1/departments",
            json={"name": "Histopathology", "code": "HISTO-01"},
            headers=self.admin_headers,
        )
        dept_id = create_res.json()["id"]

        # Update
        patch_res = self.client.patch(
            f"/api/v1/departments/{dept_id}",
            json={"description": "Updated description"},
            headers=self.admin_headers,
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.json()["description"], "Updated description")

        # Deactivate
        deact_res = self.client.patch(
            f"/api/v1/departments/{dept_id}/status",
            json={"is_active": False},
            headers=self.admin_headers,
        )
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)
        self.assertFalse(deact_res.json()["is_active"])

        # Reactivate
        react_res = self.client.patch(
            f"/api/v1/departments/{dept_id}/status",
            json={"is_active": True},
            headers=self.admin_headers,
        )
        self.assertEqual(react_res.status_code, status.HTTP_200_OK)
        self.assertTrue(react_res.json()["is_active"])

    def test_06_test_case_with_department(self):
        # 1. Create a department
        dept_res = self.client.post(
            "/api/v1/departments",
            json={"name": "Hematology Lab", "code": "HEM-LAB"},
            headers=self.admin_headers,
        )
        dept_id = dept_res.json()["id"]

        # 2. Create a test case referencing the department
        tc_res = self.client.post(
            "/api/v1/test-cases",
            json={
                "name": "Complete Blood Count",
                "code": "CBC_001",
                "price": 350.00,
                "department_id": dept_id,
            },
            headers=self.admin_headers,
        )
        self.assertEqual(tc_res.status_code, status.HTTP_201_CREATED)
        tc_data = tc_res.json()
        self.assertEqual(tc_data["department_id"], dept_id)
        self.assertIsNotNone(tc_data.get("department"))
        self.assertEqual(tc_data["department"]["name"], "Hematology Lab")

        # 3. List test cases filtered by department_id
        list_res = self.client.get(
            f"/api/v1/test-cases?department_id={dept_id}",
            headers=self.tech_headers,
        )
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(list_res.json()), 1)
