from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.bill import BillStatus


class ModeCollectionSummary(BaseModel):
    payment_mode: str
    count: int
    total_amount: Decimal


class DailyCollectionReport(BaseModel):
    report_date: date
    generated_at: datetime
    total_transactions: int
    total_collected: Decimal
    by_payment_mode: list[ModeCollectionSummary]


class PendingDueItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bill_id: int
    bill_number: str
    bill_date: datetime
    status: BillStatus
    is_cancelled: bool

    patient_id: int
    patient_uhid: str
    patient_name: str
    patient_phone: str | None = None

    doctor_name: str | None = None
    subtotal: Decimal
    discount_amount: Decimal
    payable_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal


class PendingDuesLedger(BaseModel):
    total_bills_with_dues: int
    total_outstanding_due: Decimal
    items: list[PendingDueItem]


class AccountDateWiseSummary(BaseModel):
    from_date: date
    to_date: date
    generated_at: datetime

    # Distinct financial dimensions (No misleading "Net Profit" conflation)
    total_bills_created: int
    total_billed_sales: Decimal
    total_discounts_given: Decimal
    total_net_sales: Decimal

    total_payments_collected: Decimal
    total_expenses_incurred: Decimal
    total_refunds_issued: Decimal

    net_cash_flow: Decimal
    active_period_dues: Decimal
