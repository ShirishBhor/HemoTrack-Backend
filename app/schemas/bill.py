from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.bill import BillStatus, DiscountType
from app.schemas.doctor import DoctorRead
from app.schemas.patient import PatientRead
from app.schemas.payment import PaymentRead
from app.schemas.user import UserRead



class BillItemCreate(BaseModel):
    test_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1, le=100)
    discount_amount: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)


class BillItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bill_id: int
    test_id: int | None = None
    test_name: str
    test_code: str
    unit_price: Decimal
    quantity: int
    discount_amount: Decimal
    line_total: Decimal
    created_at: datetime


class BillCreate(BaseModel):
    patient_id: int = Field(gt=0)
    doctor_id: int | None = None
    items: list[BillItemCreate] = Field(min_length=1)
    discount_type: DiscountType = DiscountType.NONE
    discount_value: Decimal = Field(default=Decimal("0.00"), ge=Decimal("0.00"), decimal_places=2)
    discount_reason: str | None = Field(default=None, max_length=255)
    remarks: str | None = None

    @model_validator(mode="after")
    def validate_discount(self) -> "BillCreate":
        if self.discount_type == DiscountType.PERCENTAGE:
            if self.discount_value > Decimal("100.00"):
                raise ValueError("Discount percentage cannot exceed 100%")
        elif self.discount_type == DiscountType.NONE:
            if self.discount_value > Decimal("0.00"):
                raise ValueError("Discount value must be 0 when discount type is NONE")
        return self


class BillCancel(BaseModel):
    reason: str = Field(min_length=3, max_length=255)

    @field_validator("reason")
    @classmethod
    def strip_reason(cls, v: str) -> str:
        cleaned = v.strip()
        if len(cleaned) < 3:
            raise ValueError("Cancellation reason must be at least 3 characters long")
        return cleaned



class BillRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    bill_number: str
    patient_id: int
    doctor_id: int | None = None
    created_by_id: int
    status: BillStatus
    subtotal: Decimal
    discount_type: DiscountType
    discount_value: Decimal
    discount_amount: Decimal
    discount_reason: str | None = None
    payable_amount: Decimal
    paid_amount: Decimal
    due_amount: Decimal
    remarks: str | None = None
    is_cancelled: bool
    cancelled_at: datetime | None = None
    cancelled_by_id: int | None = None
    cancellation_reason: str | None = None
    created_at: datetime
    updated_at: datetime

    items: list[BillItemRead] = []
    payments: list["PaymentRead"] = []
    patient: PatientRead | None = None
    doctor: DoctorRead | None = None
    created_by_user: UserRead | None = None

