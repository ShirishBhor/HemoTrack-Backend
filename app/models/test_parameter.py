
"""
Author: Nikhil Yuvraj Mole
Description:
Stores master information about parameters associated with
laboratory test cases. Patient-specific results are stored separately.
"""

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.parameter_reference_range import ParameterReferenceRange
    from app.models.test_case import TestCase


class TestParameter(Base):
    __tablename__ = "test_parameters"

    __table_args__ = (
        UniqueConstraint(
            "test_case_id",
            "code",
            name="uq_test_parameters_test_case_code",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    test_case_id: Mapped[int] = mapped_column(
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
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
        index=True,
    )

    unit: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    normal_range: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    data_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="number",
        server_default="number",
    )

    # Comma-separated or JSON list of selectable values for select data_type
    options: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Calculated parameter support (e.g. Globulin = TP - ALB)
    is_calculated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    formula: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    # Critical / Panic alert boundaries (e.g., Potassium < 2.5 or > 6.5)
    critical_low: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    critical_high: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    critical_action: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    is_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default="1",
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
        server_default="1",
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

    test_case = relationship(
        "TestCase",
        back_populates="parameters",
    )

    reference_ranges: Mapped[list["ParameterReferenceRange"]] = relationship(
        "ParameterReferenceRange",
        back_populates="parameter",
        cascade="all, delete-orphan",
    )