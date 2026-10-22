"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This model stores master information about laboratory tests.
Patient-specific test results and discounts are not stored
in this table.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

if TYPE_CHECKING:
    from app.models.test_parameter import TestParameter
    from app.models.bill import BillItem
    from app.models.test_category import TestCategory

from app.db.base import Base


class TestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    code: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    sample_type: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=0,
    )

    tat: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    category_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("test_categories.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    parameters: Mapped[list["TestParameter"]] = relationship(
        "TestParameter",
        back_populates="test_case",
        order_by="TestParameter.display_order",
        cascade="all, delete-orphan",
    )

    bill_items: Mapped[list["BillItem"]] = relationship(
        "BillItem",
        back_populates="test",
    )

    category: Mapped["TestCategory | None"] = relationship(
        "TestCategory",
        back_populates="test_cases",
    )