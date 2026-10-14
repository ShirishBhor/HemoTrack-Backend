import enum
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RefundMode(str, enum.Enum):
    CASH = "CASH"
    UPI = "UPI"
    ORIGINAL_PAYMENT_MODE = "ORIGINAL_PAYMENT_MODE"
    BANK_TRANSFER = "BANK_TRANSFER"


class Refund(Base):
    __tablename__ = "refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    refund_number: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    bill_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    refund_mode: Mapped[RefundMode] = mapped_column(
        Enum(RefundMode, name="refund_mode", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=RefundMode.CASH,
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    transaction_ref: Mapped[str | None] = mapped_column(String(100), nullable=True)

    processed_by_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )
    refund_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    bill = relationship("Bill", backref="refunds")
    processed_by_user = relationship("User", foreign_keys=[processed_by_id], backref="refunds_processed")
