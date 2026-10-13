from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.payment import PaymentMode
from app.schemas.user import UserRead


class PaymentCreate(BaseModel):
    bill_id: int = Field(gt=0)
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    payment_mode: PaymentMode = PaymentMode.CASH
    transaction_ref: str | None = Field(default=None, max_length=100)
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    receipt_number: str
    bill_id: int
    amount: Decimal
    payment_mode: PaymentMode
    transaction_ref: str | None = None
    notes: str | None = None
    received_by_id: int
    payment_date: datetime
    created_at: datetime
    updated_at: datetime

    received_by_user: UserRead | None = None
