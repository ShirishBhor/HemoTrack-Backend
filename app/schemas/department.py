"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-22

Description:
Defines validation schemas for Department APIs.
"""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


class DepartmentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Department name cannot be empty.")

        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        value = value.strip().upper()

        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError(
                "Department code can contain only letters, "
                "numbers, hyphens, and underscores."
            )

        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=150,
    )
    code: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )
    description: str | None = None
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_required_fields(cls, value):
        if isinstance(value, dict):
            for field in ("name", "code", "is_active"):
                if field in value and value[field] is None:
                    raise ValueError(f"{field} cannot be null.")

        return value

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        if not value:
            raise ValueError("Department name cannot be empty.")

        return value

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().upper()

        if not re.fullmatch(r"[A-Z0-9_-]+", value):
            raise ValueError(
                "Department code can contain only letters, "
                "numbers, hyphens, and underscores."
            )

        return value

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value or None


class DepartmentRead(DepartmentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# Backward-compatible aliases
TestCategoryBase = DepartmentBase
TestCategoryCreate = DepartmentCreate
TestCategoryUpdate = DepartmentUpdate
TestCategoryRead = DepartmentRead
