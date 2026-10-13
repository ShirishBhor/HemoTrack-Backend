"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-13

Description:
Stores age- and gender-specific normal reference ranges for laboratory
test parameters.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.test_parameter import TestParameter


class ParameterReferenceRange(Base):
    __tablename__ = "parameter_reference_ranges"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    parameter_id: Mapped[int] = mapped_column(
        ForeignKey("test_parameters.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Gender filter: 'all', 'male', 'female', 'other'
    gender: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="all",
        server_default="all",
    )

    # Age boundaries expressed in total days
    min_age_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    max_age_days: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=54750,  # ~150 years
        server_default="54750",
    )

    # Optional descriptive label (e.g., 'Adult', 'Infant', 'Pediatric')
    age_group_label: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    # Numerical range boundaries
    min_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
    )

    max_value: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 4),
        nullable=True,
    )

    # Textual display of normal range (e.g., '13.0 - 17.0 g/dL' or 'Negative')
    normal_range_text: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
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

    parameter: Mapped["TestParameter"] = relationship(
        "TestParameter",
        back_populates="reference_ranges",
    )
