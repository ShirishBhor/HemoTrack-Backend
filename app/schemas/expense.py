from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.expense import ExpenseCategory, ExpensePaymentMode
from app.schemas.user import UserRead


class ExpenseCreate(BaseModel):
    category: ExpenseCategory
    amount: Decimal = Field(gt=Decimal("0.00"), decimal_places=2)
    payment_mode: ExpensePaymentMode = ExpensePaymentMode.CASH
    expense_date: date
    payee: str | None = Field(default=None, max_length=255)
    description: str | None = None
    receipt_ref: str | None = Field(default=None, max_length=100)


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    voucher_number: str
    category: ExpenseCategory
    amount: Decimal
    payment_mode: ExpensePaymentMode
    expense_date: date
    payee: str | None = None
    description: str | None = None
    receipt_ref: str | None = None
    created_by_id: int
    created_at: datetime
    updated_at: datetime

    created_by_user: UserRead | None = None
