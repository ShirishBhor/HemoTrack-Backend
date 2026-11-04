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
from app.models.agent import Agent
from app.models.test_case import TestCase
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestAgentAPI(unittest.TestCase):
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

    def test_create_and_get_agent(self):
        payload = {
            "name": "Ajay Shinde",
            "phone": "9822334455",
            "email": "ajay.shinde@agents.com",
            "address": "Shivajinagar, Pune",
            "commission_percent": 12.0,
        }
        res = self.client.post(
            "/api/v1/agents",
            json=payload,
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        data = res.json()
        self.assertEqual(data["name"], "Ajay Shinde")
        self.assertEqual(data["phone"], "9822334455")
        self.assertEqual(data["email"], "ajay.shinde@agents.com")
        self.assertEqual(float(data["commission_percent"]), 12.0)
        self.assertTrue(data["is_active"])
        agent_id = data["id"]

        # Fetch by ID
        get_res = self.client.get(
            f"/api/v1/agents/{agent_id}",
            headers=self.tech_headers,
        )
        self.assertEqual(get_res.status_code, status.HTTP_200_OK)
        self.assertEqual(get_res.json()["id"], agent_id)

    def test_receptionist_can_create_and_update(self):
        payload = {
            "name": "Vijay Deshmukh",
            "phone": "9822334456",
            "commission_percent": 8.5,
        }
        res = self.client.post(
            "/api/v1/agents",
            json=payload,
            headers=self.recep_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        agent_id = res.json()["id"]

        # Update
        patch_res = self.client.patch(
            f"/api/v1/agents/{agent_id}",
            json={"address": "Camp, Pune"},
            headers=self.recep_headers,
        )
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.json()["address"], "Camp, Pune")

    def test_tech_cannot_create_or_update_or_deactivate(self):
        payload = {"name": "Unauthorized Agent"}
        res = self.client.post(
            "/api/v1/agents",
            json=payload,
            headers=self.tech_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_403_FORBIDDEN)

    def test_duplicate_phone_or_email_conflict(self):
        payload1 = {
            "name": "Agent A",
            "phone": "9123456781",
            "email": "unique@agent.com",
        }
        res1 = self.client.post("/api/v1/agents", json=payload1, headers=self.admin_headers)
        self.assertEqual(res1.status_code, status.HTTP_201_CREATED)

        # Duplicate phone
        res_dup_phone = self.client.post(
            "/api/v1/agents",
            json={"name": "Agent B", "phone": "9123456781"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_dup_phone.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("phone", res_dup_phone.json()["detail"].lower())

        # Duplicate email
        res_dup_email = self.client.post(
            "/api/v1/agents",
            json={"name": "Agent C", "email": "unique@agent.com"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_dup_email.status_code, status.HTTP_409_CONFLICT)
        self.assertIn("email", res_dup_email.json()["detail"].lower())

    def test_phone_validation_indian_mobile(self):
        # Invalid: starts with 4
        res_bad1 = self.client.post(
            "/api/v1/agents",
            json={"name": "Bad Phone 1", "phone": "4123456789"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_bad1.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Invalid: 11 digits
        res_bad2 = self.client.post(
            "/api/v1/agents",
            json={"name": "Bad Phone 2", "phone": "98765432100"},
            headers=self.admin_headers,
        )
        self.assertEqual(res_bad2.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_commission_percent_validation(self):
        # Exceeds 100
        res = self.client.post(
            "/api/v1/agents",
            json={"name": "Bad Commission", "commission_percent": 101.0},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

        # Below 0
        res2 = self.client.post(
            "/api/v1/agents",
            json={"name": "Bad Commission 2", "commission_percent": -1.0},
            headers=self.admin_headers,
        )
        self.assertEqual(res2.status_code, status.HTTP_422_UNPROCESSABLE_ENTITY)

    def test_list_and_search_agents(self):
        # Seed 3 agents
        for i in range(1, 4):
            self.client.post(
                "/api/v1/agents",
                json={
                    "name": f"Agent Specialist {i}",
                    "phone": f"800000000{i}",
                    "email": f"agent{i}@test.com",
                },
                headers=self.admin_headers,
            )

        # List all
        list_res = self.client.get("/api/v1/agents", headers=self.admin_headers)
        self.assertEqual(list_res.status_code, status.HTTP_200_OK)
        data = list_res.json()
        self.assertEqual(data["total"], 3)
        self.assertEqual(len(data["items"]), 3)

        # Search by email
        search_res = self.client.get(
            "/api/v1/agents?search=agent2@test.com",
            headers=self.admin_headers,
        )
        self.assertEqual(search_res.status_code, status.HTTP_200_OK)
        search_data = search_res.json()
        self.assertEqual(search_data["total"], 1)
        self.assertEqual(search_data["items"][0]["email"], "agent2@test.com")

    def test_deactivate_and_reactivate_agent(self):
        res = self.client.post(
            "/api/v1/agents",
            json={"name": "Temporary Agent", "phone": "8877665544"},
            headers=self.admin_headers,
        )
        agent_id = res.json()["id"]

        # Receptionist cannot deactivate
        res_recep_deact = self.client.patch(
            f"/api/v1/agents/{agent_id}/deactivate",
            headers=self.recep_headers,
        )
        self.assertEqual(res_recep_deact.status_code, status.HTTP_403_FORBIDDEN)

        # Admin deactivates
        deact_res = self.client.patch(
            f"/api/v1/agents/{agent_id}/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(deact_res.status_code, status.HTTP_200_OK)
        self.assertFalse(deact_res.json()["is_active"])

        # Deactivating already inactive returns 400
        deact_again = self.client.patch(
            f"/api/v1/agents/{agent_id}/deactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(deact_again.status_code, status.HTTP_400_BAD_REQUEST)

        # Excluded from active_only list
        list_active = self.client.get("/api/v1/agents?is_active=true", headers=self.admin_headers)
        self.assertEqual(list_active.json()["total"], 0)

        # Included when active_only=false
        list_all = self.client.get("/api/v1/agents", headers=self.admin_headers)
        self.assertEqual(list_all.json()["total"], 1)

        # Admin reactivates
        react_res = self.client.patch(
            f"/api/v1/agents/{agent_id}/reactivate",
            headers=self.admin_headers,
        )
        self.assertEqual(react_res.status_code, status.HTTP_200_OK)
        self.assertTrue(react_res.json()["is_active"])

    def test_patient_integration_and_filtering(self):
        # 1. Create agent
        res = self.client.post(
            "/api/v1/agents",
            json={"name": "Kiran Rao", "phone": "9811223355"},
            headers=self.admin_headers,
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        agent_id = res.json()["id"]

        # 2. Register patient linked to this agent
        patient_payload = {
            "name": "Manish Pandey",
            "gender": "male",
            "patient_type": "IPD",
            "phone": "9876543288",
            "agent_id": agent_id,
        }
        res_pat = self.client.post("/api/v1/patients", json=patient_payload, headers=self.admin_headers)
        self.assertEqual(res_pat.status_code, status.HTTP_201_CREATED)
        pat_data = res_pat.json()
        self.assertEqual(pat_data["agent_id"], agent_id)
        self.assertIsNotNone(pat_data["agent"])
        self.assertEqual(pat_data["agent"]["name"], "Kiran Rao")

        # 3. Filter patients via GET /patients?agent_id=...
        filter_res = self.client.get(f"/api/v1/patients?agent_id={agent_id}", headers=self.admin_headers)
        self.assertEqual(filter_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(filter_res.json()), 1)
        self.assertEqual(filter_res.json()[0]["name"], "Manish Pandey")

        # 4. Get via GET /agents/{id}/patients
        subroute_res = self.client.get(f"/api/v1/agents/{agent_id}/patients", headers=self.admin_headers)
        self.assertEqual(subroute_res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(subroute_res.json()), 1)
        self.assertEqual(subroute_res.json()[0]["id"], pat_data["id"])

        # 5. Invalid/inactive agent_id rejection
        bad_pat = {
            "name": "Invalid Agent Patient",
            "gender": "female",
            "agent_id": 99999,
        }
        res_bad = self.client.post("/api/v1/patients", json=bad_pat, headers=self.admin_headers)
        self.assertEqual(res_bad.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("agent", res_bad.json()["detail"].lower())

    def test_agent_stats_and_commissions(self):
        # 1. Create a test case
        db = self.TestingSessionLocal()
        tc = TestCase(
            name="Liver Function Test",
            code="LFT-001",
            price=Decimal("1500.00"),
            is_active=True,
        )
        db.add(tc)
        db.commit()
        db.refresh(tc)
        tc_id = tc.id
        db.close()

        # 2. Create agent with 15% commission
        res_agent = self.client.post(
            "/api/v1/agents",
            json={"name": "Sanjay Kapoor", "phone": "9855443322", "commission_percent": 15.0},
            headers=self.admin_headers,
        )
        self.assertEqual(res_agent.status_code, status.HTTP_201_CREATED)
        agent_id = res_agent.json()["id"]

        # 3. Register patient linked to agent
        res_pat = self.client.post(
            "/api/v1/patients",
            json={"name": "Anil Mehta", "gender": "male", "agent_id": agent_id},
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

        # 5. Make full payment of 1500
        pay_payload = {
            "bill_id": bill_id,
            "amount": 1500.0,
            "payment_mode": "UPI",
        }
        res_pay = self.client.post("/api/v1/payments", json=pay_payload, headers=self.admin_headers)
        self.assertEqual(res_pay.status_code, status.HTTP_201_CREATED)

        # 6. Fetch stats
        res_stats = self.client.get(f"/api/v1/agents/{agent_id}/stats", headers=self.admin_headers)
        self.assertEqual(res_stats.status_code, status.HTTP_200_OK)
        stats = res_stats.json()
        self.assertEqual(stats["agent_id"], agent_id)
        self.assertEqual(stats["total_patients"], 1)
        self.assertEqual(stats["total_bills"], 1)
        self.assertEqual(float(stats["total_billed_amount"]), 1500.0)
        self.assertEqual(float(stats["total_paid_amount"]), 1500.0)
        self.assertEqual(float(stats["total_commission_earned"]), 225.0)  # 15% of 1500 = 225
        self.assertEqual(len(stats["recent_bills"]), 1)
        self.assertEqual(stats["recent_bills"][0]["bill_id"], bill_id)

        # 7. Check accounts referrals summary
        res_acc = self.client.get("/api/v1/accounts/referrals-summary", headers=self.admin_headers)
        self.assertEqual(res_acc.status_code, status.HTTP_200_OK)
        acc_data = res_acc.json()
        self.assertGreaterEqual(float(acc_data["total_agents_commission"]), 225.0)
        found = any(a["id"] == agent_id and float(a["commission_earned"]) == 225.0 for a in acc_data["agents"])
        self.assertTrue(found)
