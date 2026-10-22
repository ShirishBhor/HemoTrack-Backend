from datetime import date, datetime, timedelta
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
from app.models.expense import Expense, ExpenseCategory, ExpensePaymentMode
from app.models.patient import Gender, Patient, PatientType
from app.models.payment import Payment, PaymentMode
from app.models.refund import Refund, RefundMode
from app.models.user import User, UserRole

SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"


class TestAccountsPhase4(unittest.TestCase):
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
            is_active=True,
        )
        patient = Patient(
            uhid="HT-2026-00001",
            name="Alice Smith",
            gender=Gender.FEMALE,
            age_years=28,
            phone="9123456780",
            patient_type=PatientType.OPD,
            is_active=True,
        )
        db.add_all([admin, manager, receptionist, doctor, patient])
        db.commit()
        db.refresh(admin)
        db.refresh(manager)
        db.refresh(receptionist)
        db.refresh(doctor)
        db.refresh(patient)

        self.admin_id = admin.id
        self.manager_id = manager.id
        self.rec_id = receptionist.id
        self.patient_id = patient.id
        self.doctor_id = doctor.id

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

    def test_01_expense_crud_and_rbac(self):
        # 1. Receptionist CANNOT create expense
        payload = {
            "category": "REAGENTS_KITS",
            "amount": "1500.00",
            "payment_mode": "UPI",
            "expense_date": str(date.today()),
            "payee": "BioRad Labs",
            "description": "Hematology Reagent Kit",
        }
        res_rec = self.client.post("/api/v1/expenses", json=payload, headers=self.rec_headers)
        self.assertEqual(res_rec.status_code, 403)

        # 2. Lab Manager can create expense
        res_mgr = self.client.post("/api/v1/expenses", json=payload, headers=self.manager_headers)
        self.assertEqual(res_mgr.status_code, 201)
        data = res_mgr.json()
        self.assertTrue(data["voucher_number"].startswith("EXP-2026-"))
        self.assertEqual(Decimal(str(data["amount"])), Decimal("1500.00"))

        # 3. Negative amount is rejected
        bad_payload = payload.copy()
        bad_payload["amount"] = "-200.00"
        res_bad = self.client.post("/api/v1/expenses", json=bad_payload, headers=self.manager_headers)
        self.assertEqual(res_bad.status_code, 422)

        # 4. List expenses
        res_list = self.client.get("/api/v1/expenses", headers=self.rec_headers)
        self.assertEqual(res_list.status_code, 200)
        self.assertEqual(len(res_list.json()), 1)

    def test_02_daily_collection_by_payment_mode(self):
        # Create a bill
        db = self.TestingSessionLocal()
        bill = Bill(
            bill_number="BILL-2026-00001",
            patient_id=self.patient_id,
            created_by_id=self.rec_id,
            status=BillStatus.UNPAID,
            subtotal=Decimal("2000.00"),
            payable_amount=Decimal("2000.00"),
            paid_amount=Decimal("0.00"),
            due_amount=Decimal("2000.00"),
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)
        bill_id = bill.id
        db.close()

        # Collect 3 payments with different modes
        # Payment 1: ₹500 via CASH
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": bill_id, "amount": "500.00", "payment_mode": "CASH"},
            headers=self.rec_headers,
        )
        # Payment 2: ₹700 via UPI
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": bill_id, "amount": "700.00", "payment_mode": "UPI", "transaction_ref": "UPI-XYZ"},
            headers=self.rec_headers,
        )
        # Payment 3: ₹300 via CARD
        self.client.post(
            "/api/v1/payments",
            json={"bill_id": bill_id, "amount": "300.00", "payment_mode": "CARD", "transaction_ref": "CARD-ABC"},
            headers=self.rec_headers,
        )

        # Check daily collection report for today
        today_str = str(date.today())
        res = self.client.get(f"/api/v1/accounts/daily-collection?report_date={today_str}", headers=self.rec_headers)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["total_transactions"], 3)
        self.assertEqual(Decimal(str(data["total_collected"])), Decimal("1500.00"))

        # Verify mode breakdown
        mode_map = {m["payment_mode"]: Decimal(str(m["total_amount"])) for m in data["by_payment_mode"]}
        self.assertEqual(mode_map["CASH"], Decimal("500.00"))
        self.assertEqual(mode_map["UPI"], Decimal("700.00"))
        self.assertEqual(mode_map["CARD"], Decimal("300.00"))
        self.assertEqual(mode_map["CHEQUE"], Decimal("0.00"))

    def test_03_pending_dues_ledger(self):
        db = self.TestingSessionLocal()
        # Bill 1: Active, due ₹600
        b1 = Bill(
            bill_number="BILL-2026-00010",
            patient_id=self.patient_id,
            created_by_id=self.rec_id,
            status=BillStatus.PARTIALLY_PAID,
            subtotal=Decimal("1000.00"),
            payable_amount=Decimal("1000.00"),
            paid_amount=Decimal("400.00"),
            due_amount=Decimal("600.00"),
            is_cancelled=False,
        )
        # Bill 2: Cancelled, due ₹500
        b2 = Bill(
            bill_number="BILL-2026-00011",
            patient_id=self.patient_id,
            created_by_id=self.rec_id,
            status=BillStatus.CANCELLED,
            subtotal=Decimal("500.00"),
            payable_amount=Decimal("500.00"),
            paid_amount=Decimal("0.00"),
            due_amount=Decimal("500.00"),
            is_cancelled=True,
        )
        db.add_all([b1, b2])
        db.commit()
        db.close()

        # 1. Normal active pending dues - excludes cancelled
        res_active = self.client.get("/api/v1/accounts/pending-dues", headers=self.rec_headers)
        self.assertEqual(res_active.status_code, 200)
        data_active = res_active.json()
        self.assertEqual(data_active["total_bills_with_dues"], 1)
        self.assertEqual(Decimal(str(data_active["total_outstanding_due"])), Decimal("600.00"))
        self.assertEqual(data_active["items"][0]["bill_number"], "BILL-2026-00010")

        # 2. Audit cancelled pending dues - includes cancelled
        res_all = self.client.get("/api/v1/accounts/pending-dues?include_cancelled=true", headers=self.rec_headers)
        self.assertEqual(res_all.status_code, 200)
        data_all = res_all.json()
        self.assertEqual(data_all["total_bills_with_dues"], 2)
        self.assertEqual(Decimal(str(data_all["total_outstanding_due"])), Decimal("1100.00"))

    def test_04_refund_workflow_and_headroom_validation(self):
        db = self.TestingSessionLocal()
        bill = Bill(
            bill_number="BILL-2026-00020",
            patient_id=self.patient_id,
            created_by_id=self.rec_id,
            status=BillStatus.PARTIALLY_PAID,
            subtotal=Decimal("1000.00"),
            payable_amount=Decimal("1000.00"),
            paid_amount=Decimal("600.00"),
            due_amount=Decimal("400.00"),
        )
        db.add(bill)
        db.commit()
        db.refresh(bill)
        bill_id = bill.id

        # Insert actual collected payment of ₹600
        p = Payment(
            receipt_number="RCP-2026-00020",
            bill_id=bill_id,
            amount=Decimal("600.00"),
            payment_mode=PaymentMode.UPI,
            received_by_id=self.rec_id,
        )
        db.add(p)
        db.commit()
        db.close()

        # 1. Receptionist CANNOT issue refund
        refund_payload = {
            "bill_id": bill_id,
            "amount": "400.00",
            "refund_mode": "UPI",
            "reason": "Test sample haemolysed and patient refused repeat draw",
        }
        res_rec = self.client.post("/api/v1/refunds", json=refund_payload, headers=self.rec_headers)
        self.assertEqual(res_rec.status_code, 403)

        # 2. Admin issues valid partial refund of ₹400
        res_adm = self.client.post("/api/v1/refunds", json=refund_payload, headers=self.admin_headers)
        self.assertEqual(res_adm.status_code, 201)
        r_data = res_adm.json()
        self.assertTrue(r_data["refund_number"].startswith("REF-2026-"))
        self.assertEqual(Decimal(str(r_data["amount"])), Decimal("400.00"))

        # 3. Attempting to refund more than remaining collected headroom (₹600 - ₹400 = ₹200) -> Rejection
        excess_payload = {
            "bill_id": bill_id,
            "amount": "250.00",
            "refund_mode": "CASH",
            "reason": "Excessive refund attempt",
        }
        res_excess = self.client.post("/api/v1/refunds", json=excess_payload, headers=self.admin_headers)
        self.assertEqual(res_excess.status_code, 400)
        self.assertIn("exceeds refundable balance", res_excess.json()["detail"].lower())

    def test_05_date_wise_account_summary_reconciliation(self):
        today = date.today()
        db = self.TestingSessionLocal()

        # 1. Bill: ₹1200 sales
        b = Bill(
            bill_number="BILL-2026-00030",
            patient_id=self.patient_id,
            created_by_id=self.rec_id,
            status=BillStatus.PARTIALLY_PAID,
            subtotal=Decimal("1200.00"),
            discount_amount=Decimal("100.00"),
            payable_amount=Decimal("1100.00"),
            paid_amount=Decimal("700.00"),
            due_amount=Decimal("400.00"),
            is_cancelled=False,
        )
        db.add(b)
        db.commit()
        db.refresh(b)

        # 2. Payment: ₹700 collected
        p = Payment(
            receipt_number="RCP-2026-00030",
            bill_id=b.id,
            amount=Decimal("700.00"),
            payment_mode=PaymentMode.CASH,
            received_by_id=self.rec_id,
        )
        # 3. Expense: ₹300 spent
        e = Expense(
            voucher_number="EXP-2026-00030",
            category=ExpenseCategory.LAB_CONSUMABLES,
            amount=Decimal("300.00"),
            payment_mode=ExpensePaymentMode.CASH,
            expense_date=today,
            created_by_id=self.admin_id,
        )
        # 4. Refund: ₹100 refunded
        r = Refund(
            refund_number="REF-2026-00030",
            bill_id=b.id,
            amount=Decimal("100.00"),
            refund_mode=RefundMode.CASH,
            reason="Partial refund",
            processed_by_id=self.admin_id,
        )
        db.add_all([p, e, r])
        db.commit()
        db.close()

        # Query summary for today
        res = self.client.get(f"/api/v1/accounts/summary?from_date={today}&to_date={today}", headers=self.admin_headers)
        self.assertEqual(res.status_code, 200)
        summary = res.json()

        self.assertEqual(summary["total_bills_created"], 1)
        self.assertEqual(Decimal(str(summary["total_billed_sales"])), Decimal("1200.00"))
        self.assertEqual(Decimal(str(summary["total_discounts_given"])), Decimal("100.00"))
        self.assertEqual(Decimal(str(summary["total_net_sales"])), Decimal("1100.00"))

        self.assertEqual(Decimal(str(summary["total_payments_collected"])), Decimal("700.00"))
        self.assertEqual(Decimal(str(summary["total_expenses_incurred"])), Decimal("300.00"))
        self.assertEqual(Decimal(str(summary["total_refunds_issued"])), Decimal("100.00"))

        # Net Cash Flow = Collected (₹700) - Expenses (₹300) - Refunds (₹100) = ₹300
        self.assertEqual(Decimal(str(summary["net_cash_flow"])), Decimal("300.00"))
        self.assertEqual(Decimal(str(summary["active_period_dues"])), Decimal("400.00"))
