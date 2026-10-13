import enum
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ExpenseCategory(str, enum.Enum):
    REAGENTS_KITS = "REAGENTS_KITS"
    LAB_CONSUMABLES = "LAB_CONSUMABLES"
    EQUIPMENT_MAINTENANCE = "EQUIPMENT_MAINTENANCE"
    UTILITIES = "UTILITIES"
    OFFICE_SUPPLIES = "OFFICE_SUPPLIES"
    SALARY_WAGES = "SALARY_WAGES"
    RENT = "RENT"
    WASTE_MANAGEMENT = "WASTE_MANAGEMENT"
    OTHER = "OTHER"


class ExpensePaymentMode(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    CARD = "CARD"
    NET_BANKING = "NET_BANKING"
    CHEQUE = "CHEQUE"


class Expense(Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    voucher_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    category: Mapped[ExpenseCategory] = mapped_column(
        Enum(ExpenseCategory, name="expense_category", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ExpenseCategory.OTHER,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    payment_mode: Mapped[ExpensePaymentMode] = mapped_column(
        Enum(ExpensePaymentMode, name="expense_payment_mode", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=ExpensePaymentMode.CASH,
    )
    expense_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payee: Mapped[str | None] = mapped_column(String(255), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    receipt_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)

    created_by_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    created_by_user = relationship("User", foreign_keys=[created_by_id], backref="expenses_recorded")
