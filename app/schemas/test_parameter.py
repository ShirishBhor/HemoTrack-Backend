"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This file defines Pydantic validation schemas for Test Parameter APIs.
It validates laboratory test parameter data before it is processed
by the service layer.
"""


from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)


ALLOWED_DATA_TYPES = {"number", "text", "select", "boolean"}


class TestParameterBase(BaseModel):
    test_case_id: int = Field(..., gt=0)
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)

    unit: str | None = Field(default=None, max_length=100)
    normal_range: str | None = Field(default=None, max_length=255)
    description: str | None = None

    data_type: str = Field(default="number", max_length=50)
    is_required: bool = True
    display_order: int = Field(default=1, gt=0)

    @field_validator("name", "code")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty or spaces only.")

        if info.field_name == "code":
            return value.upper()

        return value

    @field_validator("unit", "normal_range", "description")
    @classmethod
    def clean_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value if value else None

    @field_validator("data_type")
    @classmethod
    def validate_data_type(cls, value: str) -> str:
        value = value.strip().lower()

        if value not in ALLOWED_DATA_TYPES:
            raise ValueError(
                "data_type must be number, text, select, or boolean."
            )

        return value


class TestParameterCreate(TestParameterBase):
    pass


class TestParameterUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    code: str | None = Field(default=None, min_length=1, max_length=100)

    unit: str | None = Field(default=None, max_length=100)
    normal_range: str | None = Field(default=None, max_length=255)
    description: str | None = None

    data_type: str | None = Field(default=None, max_length=50)
    is_required: bool | None = None
    display_order: int | None = Field(default=None, gt=0)
    is_active: bool | None = None

    @model_validator(mode="before")
    @classmethod
    def reject_null_for_required_fields(cls, value):
        if isinstance(value, dict):
            non_nullable = {
                "name",
                "code",
                "data_type",
                "is_required",
                "display_order",
                "is_active",
            }

            for field in non_nullable:
                if field in value and value[field] is None:
                    raise ValueError(f"{field} cannot be null")

        return value

    @field_validator("name", "code")
    @classmethod
    def clean_update_text(cls, value: str | None, info) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Value cannot be empty or spaces only.")

        if info.field_name == "code":
            return value.upper()

        return value

    @field_validator("unit", "normal_range", "description")
    @classmethod
    def clean_update_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()
        return value if value else None

    @field_validator("data_type")
    @classmethod
    def validate_update_data_type(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip().lower()

        if value not in ALLOWED_DATA_TYPES:
            raise ValueError(
                "data_type must be number, text, select, or boolean."
            )

        return value


class TestParameterRead(TestParameterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime