from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.refund import RefundMode
from app.schemas.user import UserRead


class RefundCreate(BaseModel):
    bill_id: int = Field(gt=0)
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    refund_mode: RefundMode = RefundMode.CASH
    reason: str = Field(min_length=3, max_length=500)
    transaction_ref: str | None = Field(default=None, max_length=100)


class RefundRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    refund_number: str
    bill_id: int
    amount: Decimal
    refund_mode: RefundMode
    reason: str
    transaction_ref: str | None = None
    processed_by_id: int
    refund_date: datetime
    created_at: datetime

    processed_by_user: UserRead | None = None
