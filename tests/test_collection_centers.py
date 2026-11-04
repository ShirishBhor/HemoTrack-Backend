import unittest
from decimal import Decimal

from fastapi import status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.deps import get_db
from app.core.security import hash_password
from app.db import Base
from app.main import app
from app.models.collection_center import CollectionCenter
from app.models.test_case import TestCase
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestCollectionCenterAPI(unittest.TestCase):
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
        receptionist = User(
            email="recep@test.com",
            hashed_password=hash_password("RecepPass123"),
            full_name="Receptionist User",
            role=UserRole.RECEPTIONIST,
            is_active=True,
        )
        db.add_all([admin, tech, receptionist])
        db.commit()

        # Login admin
        res_admin = self.client.post(
            "/api/v1/auth/login",
            json={"email": "admin@test.com", "password": "AdminPass123"},
        )
        self.assertEqual(res_admin.status_code, 200)
        self.admin_headers = {"Authorization": f"Bearer {res_admin.json()['access_token']}"}

        # Login tech
        res_tech = self.client.post(
            "/api/v1/auth/login",
            json={"email": "tech@test.com", "password": "TechPass123"},
        )
        self.assertEqual(res_tech.status_code, 200)
        self.tech_headers = {"Authorization": f"Bearer {res_tech.json()['access_token']}"}

        # Login receptionist
        res_recep = self.client.post(
            "/api/v1/auth/login",
            json={"email": "recep@test.com", "password": "RecepPass123"},
        )
        self.assertEqual(res_recep.status_code, 200)
        self.recep_headers = {"Authorization": f"Bearer {res_recep.json()['access_token']}"}

        db.close()

    def tearDown(self):
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()

    def test_create_and_get_collection_center(self):
        payload = {
            "name": "Kothrud Collection Point",
            "phone": "9876543210",
            "email": "kothrud@pathology.com",
            "address": "Vanaz Corner, Paud Road, Pune",
            "contact_person": "Sunil More",
            "commission_percent": 15.5,
        }
        res = self.client.post(
            "/api/v1/collection-centers",
            json=payload,
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["name"], "Kothrud Collection Point")
        self.assertEqual(data["phone"], "9876543210")
        self.assertEqual(data["email"], "kothrud@pathology.com")
        self.assertEqual(data["contact_person"], "Sunil More")
        self.assertEqual(float(data["commission_percent"]), 15.5)
        self.assertTrue(data["is_active"])
        center_id = data["id"]

        # Fetch by ID
        get_res = self.client.get(
            f"/api/v1/collection-centers/{center_id}",
            headers=self.tech_headers,
        )
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.json()["id"], center_id)

    def test_receptionist_can_create_and_update(self):
        payload = {
            "name": "Aundh Branch",
            "phone": "9876543211",
            "commission_percent": 10.0,
        }
        res = self.client.post(
            "/api/v1/collection-centers",
            json=payload,
            headers=self.recep_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        center_id = res.json()["id"]

        # Update
        patch_res = self.client.patch(
            f"/api/v1/collection-centers/{center_id}",
            json={"contact_person": "Ramesh Patil"},
            headers=self.recep_headers,
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.json()["contact_person"], "Ramesh Patil")

    def test_tech_cannot_create_or_update_or_deactivate(self):
        payload = {"name": "Unauthorized Center"}
        res = self.client.post(
            "/api/v1/collection-centers",
            json=payload,
            headers=self.tech_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_phone_or_email_conflict(self):
        payload1 = {
            "name": "Center A",
            "phone": "9123456780",
            "email": "unique@center.com",
        }
        res1 = self.client.post("/api/v1/collection-centers", json=payload1, headers=self.admin_headers)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Duplicate phone
        res_dup_phone = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Center B", "phone": "9123456780"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_dup_phone.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("phone", res_dup_phone.json()["detail"].lower())

        # Duplicate email
        res_dup_email = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Center C", "email": "unique@center.com"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_dup_email.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("email", res_dup_email.json()["detail"].lower())

    def test_phone_validation_indian_mobile(self):
        # Invalid: starts with 5
        res_bad1 = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Bad Phone 1", "phone": "5123456789"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_bad1.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Invalid: 9 digits
        res_bad2 = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Bad Phone 2", "phone": "987654321"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_bad2.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_commission_percent_validation(self):
        # Exceeds 100
        res = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Bad Commission", "commission_percent": 105.0},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Below 0
        res2 = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Bad Commission 2", "commission_percent": -5.0},
            headers=self.admin_headers,
        )
        self.assertEqual(res2.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_list_and_search_collection_centers(self):
        # Seed 3 collection centers
        for i in range(1, 4):
            self.client.post(
                "/api/v1/collection-centers",
                json={
                    "name": f"Center Location {i}",
                    "phone": f"900000000{i}",
                    "contact_person": f"Manager {i}",
                },
                headers=self.admin_headers,
            )

        # List all
        list_res = self.client.get("/api/v1/collection-centers", headers=self.admin_headers)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        data = list_res.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 3)

        # Search by contact person
        search_res = self.client.get(
            "/api/v1/collection-centers?search=Manager 2",
            headers=self.admin_headers,
        )
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        search_data = search_res.json()
        self.assertEqual(search_data["total"], 1)
        self.assertEqual(search_data["items"][0]["contact_person"], "Manager 2")

    def test_deactivate_and_reactivate_collection_center(self):
        res = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Temporary Center", "phone": "9988776655"},
            headers=self.admin_headers,
        )
        center_id = res.json()["id"]

        # Receptionist cannot deactivate
        res_recep_deact = self.client.patch(
            f"/api/v1/collection-centers/{center_id}/deactivate",
            headers=self.recep_headers,
        )
        self.assertEqual(res_recep_deact.status_code, status.HTTP_403_FORBIDDEN)

        # Admin deactivates
        deact_res = self.client.patch(
            f"/api/v1/collection-centers/{center_id}/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)
        self.assertFalse(deact_res.json()["is_active"])

        # Deactivating already inactive returns 400
        deact_again = self.client.patch(
            f"/api/v1/collection-centers/{center_id}/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(deact_again.status_code, status.HTTP_400_BAD_REQUEST)

        # Excluded from active_only list
        list_active = self.client.get("/api/v1/collection-centers?is_active=true", headers=self.admin_headers)
        self.assertEqual(list_active.json()["total"], 0)

        # Included when active_only=false
        list_all = self.client.get("/api/v1/collection-centers", headers=self.admin_headers)
        self.assertEqual(list_all.json()["total"], 1)

        # Admin reactivates
        react_res = self.client.patch(
            f"/api/v1/collection-centers/{center_id}/reactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(react_res.status_code, status.HTTP_200_OK)
        self.assertTrue(react_res.json()["is_active"])

    def test_patient_integration_and_filtering(self):
        # 1. Create collection center
        res = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Baner Collection Hub", "phone": "9811223344"},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        center_id = res.json()["id"]

        # 2. Register patient linked to this collection center
        patient_payload = {
            "name": "Suresh Raina",
            "gender": "male",
            "patient_type": "OPD",
            "phone": "9876543299",
            "collection_center_id": center_id,
        }
        res_pat = self.client.post("/api/v1/patients", json=patient_payload, headers=self.admin_headers)
        self.assertEqual(res_pat.status_code, status.HTTP_201_CREATED)
        pat_data = res_pat.json()
        self.assertEqual(pat_data["collection_center_id"], center_id)
        self.assertIsNotNone(pat_data["collection_center"])
        self.assertEqual(pat_data["collection_center"]["name"], "Baner Collection Hub")

        # 3. Filter patients via GET /patients?collection_center_id=...
        filter_res = self.client.get(f"/api/v1/patients?collection_center_id={center_id}", headers=self.admin_headers)
        self.assertEqual(filter_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filter_res.json()), 1)
        self.assertEqual(filter_res.json()[0]["name"], "Suresh Raina")

        # 4. Get via GET /collection-centers/{id}/patients
        subroute_res = self.client.get(f"/api/v1/collection-centers/{center_id}/patients", headers=self.admin_headers)
        self.assertEqual(subroute_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(subroute_res.json()), 1)
        self.assertEqual(subroute_res.json()[0]["id"], pat_data["id"])

        # 5. Invalid/inactive collection_center_id rejection
        bad_pat = {
            "name": "Invalid Center Patient",
            "gender": "male",
            "collection_center_id": 99999,
        }
        res_bad = self.client.post("/api/v1/patients", json=bad_pat, headers=self.admin_headers)
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("collection center", res_bad.json()["detail"].lower())

    def test_collection_center_stats_and_commissions(self):
        # 1. Create a test case
        db = self.TestingSessionLocal()
        tc = TestCase(
            name="Complete Blood Count",
            code="CBC-001",
            price=Decimal("1000.00"),
            is_active=True,
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)
        tc_id = tc.id
        db.close()

        # 2. Create collection center with 10% commission
        res_center = self.client.post(
            "/api/v1/collection-centers",
            json={"name": "Kalyani Nagar Center", "phone": "9866554433", "commission_percent": 10.0},
            headers=self.admin_headers,
        )
        self.assertEqual(res_center.status_code, status.HTTP_201_CREATED)
        center_id = res_center.json()["id"]

        # 3. Register patient linked to center
        res_pat = self.client.post(
            "/api/v1/patients",
            json={"name": "Rohit Verma", "gender": "male", "collection_center_id": center_id},
            headers=self.admin_headers,
        )
        self.assertEqual(res_pat.status_code, status.HTTP_201_CREATED)
        patient_id = res_pat.json()["id"]

        # 4. Create bill
        bill_payload = {
            "patient_id": patient_id,
            "items": [{"test_id": tc_id, "quantity": 1}],
        }
        res_bill = self.client.post("/api/v1/bills", json=bill_payload, headers=self.admin_headers)
        self.assertEqual(res_bill.status_code, status.HTTP_201_CREATED)
        bill_id = res_bill.json()["id"]

        # 5. Make partial payment of 500
        pay_payload = {
            "bill_id": bill_id,
            "amount": 500.0,
            "payment_mode": "CASH",
        }
        res_pay = self.client.post("/api/v1/payments", json=pay_payload, headers=self.admin_headers)
        self.assertEqual(res_pay.status_code, status.HTTP_201_CREATED)

        # 6. Fetch stats
        res_stats = self.client.get(f"/api/v1/collection-centers/{center_id}/stats", headers=self.admin_headers)
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        stats = res_stats.json()
        self.assertEqual(stats["center_id"], center_id)
        self.assertEqual(stats["total_patients"], 1)
        self.assertEqual(stats["total_bills"], 1)
        self.assertEqual(float(stats["total_billed_amount"]), 1000.0)
        self.assertEqual(float(stats["total_paid_amount"]), 500.0)
        self.assertEqual(float(stats["total_commission_earned"]), 100.0)
        self.assertEqual(len(stats["recent_bills"]), 1)
        self.assertEqual(stats["recent_bills"][0]["bill_id"], bill_id)

        # 7. Check accounts referrals summary
        res_acc = self.client.get("/api/v1/accounts/referrals-summary", headers=self.admin_headers)
        self.assertEqual(res_acc.status_code, status.HTTP_200_OK)
        acc_data = res_acc.json()
        self.assertGreaterEqual(float(acc_data["total_centers_commission"]), 100.0)
        found = any(c["id"] == center_id and float(c["commission_earned"]) == 100.0 for c in acc_data["collection_centers"])
        self.assertTrue(found)
