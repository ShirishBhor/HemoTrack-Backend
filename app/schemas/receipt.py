from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.bill import BillStatus, DiscountType
from app.models.payment import PaymentMode


class ReceiptPatientInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uhid: str
    name: str
    gender: str
    age_years: int
    age_months: int
    age_days: int
    phone: str | None = None
    email: str | None = None
    address: str | None = None
    collection_center_name: str | None = None
    agent_name: str | None = None


class ReceiptDoctorInfo(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    specialization: str | None = None
    phone: str | None = None


class ReceiptBillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    test_code: str
    test_name: str
    unit_price: Decimal
    quantity: int
    discount_amount: Decimal
    line_total: Decimal


class ReceiptPaymentEntry(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    receipt_number: str
    amount: Decimal
    payment_mode: PaymentMode
    transaction_ref: str | None = None
    payment_date: datetime
    received_by_name: str | None = None


class LabHeaderInfo(BaseModel):
    lab_name: str = "HemoTrack Diagnostic Center"
    tagline: str = "Precision Pathology & Clinical Laboratory"
    address: str = "101 Healthcare Avenue, Medical District"
    phone: str = "+91 98765 43210"
    email: str = "support@hemotrack.com"
    website: str = "https://hemotrack.com"


class PrintableReceipt(BaseModel):
    lab_header: LabHeaderInfo = LabHeaderInfo()
    bill_id: int
    bill_number: str
    bill_date: datetime
    status: BillStatus
    is_cancelled: bool
    cancellation_reason: str | None = None
    cancelled_at: datetime | None = None
    cancelled_by_name: str | None = None

    patient: ReceiptPatientInfo
    doctor: ReceiptDoctorInfo | None = None
    billed_by_name: str

    items: list[ReceiptBillItem]
    subtotal: Decimal
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal
    discount_reason: str | None = None
    payable_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    remarks: str | None = None

    payments: list[ReceiptPaymentEntry] = []
    generated_at: datetime
