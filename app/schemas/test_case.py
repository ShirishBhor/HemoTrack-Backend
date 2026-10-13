"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This file defines Pydantic validation schemas for Test Case APIs.
It validates laboratory test data before it is processed by the service layer.

Patient-specific test results and discounts are not stored in these schemas.
"""

import re
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.test_parameter import TestParameterRead


class TestCaseBase(BaseModel):
    name: str = Field(
        ...,
        min_length=1,
        max_length=255,
    )

    code: str = Field(
        ...,
        min_length=1,
        max_length=100,
    )

    description: str | None = None

    sample_type: str | None = Field(
        default=None,
        max_length=100,
    )

    price: Decimal = Field(
        ...,
        ge=0,
        decimal_places=2,
        max_digits=10,
        description="Current master price of the test",
    )

    tat: str | None = Field(
        default=None,
        max_length=100,
        description="Turnaround time for the test",
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Test name cannot be empty")

        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        value = value.strip().upper()

        if not value:
            raise ValueError("Test code cannot be empty")

        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError(
                "Test code can contain only letters, numbers, "
                "hyphens, and underscores"
            )

        return value

    @field_validator("description", "sample_type", "tat")
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value if value else None


class TestCaseCreate(TestCaseBase):
    pass


class TestCaseUpdate(BaseModel):
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

    sample_type: str | None = Field(
        default=None,
        max_length=100,
    )

    price: Decimal | None = Field(
        default=None,
        ge=0,
        decimal_places=2,
        max_digits=10,
        description="Updated master price of the test",
    )

    tat: str | None = Field(
        default=None,
        max_length=100,
    )

    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Test name cannot be empty")

        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        if not value:
            raise ValueError("Test code cannot be empty")

        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError(
                "Test code can contain only letters, numbers, "
                "hyphens, and underscores"
            )

        return value

    @field_validator("description", "sample_type", "tat")
    @classmethod
    def clean_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value if value else None


class TestCaseRead(TestCaseBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TestCaseWithParametersRead(TestCaseRead):
    parameters: list[TestParameterRead] = []