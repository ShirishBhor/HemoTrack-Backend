"""
Author: Nikhil Yuvraj Mole
Date: 2026-11-02

Description:
Pydantic validation schemas for Package Master APIs.
Validates health package data and test associations.
"""

import re
from datetime import datetime
from decimal import Decimal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.schemas.department import DepartmentRead
from app.schemas.test_case import TestCaseRead


class PackageBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
        description="Name of the health package",
    )

    code: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Unique package code",
    )

    description: str | None = Field(
        default=None,
        description="Package description and instructions",
    )

    price: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        max_digits=10,
        description="Discounted bundle price of the package",
    )

    tat: str | None = Field(
        default=None,
        max_length=100,
        description="Turnaround time (e.g. '24 Hours')",
    )

    sample_requirements: str | None = Field(
        default=None,
        max_length=255,
        description="Sample requirements (e.g. 'Fasting Blood, Spot Urine')",
    )

    fasting_required: bool = Field(
        default=False,
        description="Whether fasting is required before sample collection",
    )

    department_id: int | None = Field(
        default=None,
        description="Optional department ID the package belongs to",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Package name cannot be empty")
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        value = value.strip().upper()
        if not value:
            raise ValueError("Package code cannot be empty")
        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError(
                "Package code can contain only uppercase letters, numbers, hyphens, and underscores"
            )
        return value

    @field_validator("description", "tat", "sample_requirements")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value if value else None


class PackageCreate(PackageBase):
    test_case_ids: list[int] = Field(
        default_factory=list,
        description="List of test case IDs included in this package",
    )


class PackageUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )

    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=100,
    )

    description: str | None = None

    price: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        max_digits=10,
    )

    tat: str | None = Field(
        default=None,
        max_length=100,
    )

    sample_requirements: str | None = Field(
        default=None,
        max_length=255,
    )

    fasting_required: bool | None = None

    department_id: int | None = Field(
        default=None,
    )

    is_active: bool | None = None

    test_case_ids: list[int] | None = Field(
        default=None,
        description="Updated list of test case IDs for this package",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Package name cannot be empty")
        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().upper()
        if not value:
            raise ValueError("Package code cannot be empty")
        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError(
                "Package code can contain only uppercase letters, numbers, hyphens, and underscores"
            )
        return value

    @field_validator("description", "tat", "sample_requirements")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        return value if value else None


class PackageTestCaseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    package_id: int
    test_case_id: int
    display_order: int
    test_case: TestCaseRead


class PackageRead(PackageBase):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    department: DepartmentRead | None = None
    test_count: int = 0


class PackageWithTestsRead(PackageRead):
    package_tests: list[PackageTestCaseRead] = []
    test_cases: list[TestCaseRead] = []
