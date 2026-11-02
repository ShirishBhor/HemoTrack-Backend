"""
Author: Nikhil Yuvraj Mole
Date: 2026-11-02

Description:
SQLAlchemy models for Package Master and Package-Test Case associations.
Enables bundling multiple laboratory test cases into discounted health packages.
"""

from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.department import Department
    from app.models.test_case import TestCase


class PackageTestCase(Base):
    __tablename__ = "package_test_cases"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    package_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("packages.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    test_case_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("test_cases.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    display_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=1,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # Relationships
    package: Mapped["Package"] = relationship(
        "Package",
        back_populates="package_tests",
    )
    test_case: Mapped["TestCase"] = relationship(
        "TestCase",
    )

    __table_args__ = (
        UniqueConstraint(
            "package_id",
            "test_case_id",
            name="uq_package_test_case",
        ),
    )


class Package(Base):
    __tablename__ = "packages"

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

    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
        default=Decimal("0.00"),
    )

    tat: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    sample_requirements: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    fasting_required: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    department_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="SET NULL"),
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

    # Relationships
    department: Mapped["Department | None"] = relationship(
        "Department",
    )
    package_tests: Mapped[list["PackageTestCase"]] = relationship(
        "PackageTestCase",
        back_populates="package",
        cascade="all, delete-orphan",
        order_by="PackageTestCase.display_order",
    )

    @property
    def test_count(self) -> int:
        return len(self.package_tests) if self.package_tests else 0

    @property
    def test_cases(self) -> list["TestCase"]:
        return [pt.test_case for pt in self.package_tests if pt.test_case is not None]

    @property
    def category(self) -> "Department | None":
        return self.department
