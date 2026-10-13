"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This file defines Pydantic validation schemas for Test Parameter APIs.
It validates laboratory test parameter data before it is processed
by the service layer.
"""


from datetime import datetime
from decimal import Decimal

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
    options: list[str] | str | None = None
    is_calculated: bool = False
    formula: str | None = Field(default=None, max_length=255)
    critical_low: str | None = Field(default=None, max_length=100)
    critical_high: str | None = Field(default=None, max_length=100)
    critical_action: str | None = None

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

    @field_validator("unit", "normal_range", "description", "formula", "critical_low", "critical_high", "critical_action")
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
    options: list[str] | str | None = None
    is_calculated: bool | None = None
    formula: str | None = Field(default=None, max_length=255)
    critical_low: str | None = Field(default=None, max_length=100)
    critical_high: str | None = Field(default=None, max_length=100)
    critical_action: str | None = None

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

    @field_validator("unit", "normal_range", "description", "formula", "critical_low", "critical_high", "critical_action")
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


class TestParameterBulkItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=100)
    unit: str | None = Field(default=None, max_length=100)
    normal_range: str | None = Field(default=None, max_length=255)
    description: str | None = None
    data_type: str = Field(default="number", max_length=50)
    options: list[str] | str | None = None
    is_calculated: bool = False
    formula: str | None = Field(default=None, max_length=255)
    critical_low: str | None = Field(default=None, max_length=100)
    critical_high: str | None = Field(default=None, max_length=100)
    critical_action: str | None = None
    is_required: bool = True
    display_order: int | None = Field(default=None, gt=0)

    @field_validator("name", "code")
    @classmethod
    def validate_required_text(cls, value: str, info) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be empty or spaces only.")
        if info.field_name == "code":
            return value.upper()
        return value

    @field_validator("unit", "normal_range", "description", "formula", "critical_low", "critical_high", "critical_action")
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
            raise ValueError("data_type must be number, text, select, or boolean.")
        return value


class TestParameterBulkCreate(BaseModel):
    parameters: list[TestParameterBulkItem] = Field(
        ...,
        min_length=1,
        description="List of test parameters to add in bulk",
    )


class ParameterOrderItem(BaseModel):
    id: int = Field(..., gt=0, alias="parameter_id", description="Test parameter ID")
    display_order: int = Field(..., gt=0, description="New display order sequence")

    model_config = ConfigDict(populate_by_name=True)


class ParameterReorderRequest(BaseModel):
    orders: list[ParameterOrderItem] = Field(
        default_factory=list,
        description="List of parameter IDs and their new display order",
    )
    parameter_ids: list[int] | None = Field(
        default=None,
        description="Alternative ordered list of parameter IDs (auto-sequenced 1, 2, 3...)",
    )


# ============================================================
# REFERENCE RANGE SCHEMAS
# ============================================================

class ParameterReferenceRangeBase(BaseModel):
    gender: str = Field(default="all", max_length=20, description="'all', 'male', 'female', or 'other'")
    min_age_days: int = Field(default=0, ge=0, description="Minimum age in days")
    max_age_days: int = Field(default=54750, ge=0, description="Maximum age in days (~150 years)")
    age_group_label: str | None = Field(default=None, max_length=100, description="Optional label like 'Adult', 'Infant'")
    min_value: Decimal | None = Field(default=None, description="Numeric lower normal boundary")
    max_value: Decimal | None = Field(default=None, description="Numeric upper normal boundary")
    normal_range_text: str | None = Field(default=None, max_length=255, description="Textual normal range (e.g. '13.0 - 17.0 g/dL')")
    notes: str | None = None

    @field_validator("gender")
    @classmethod
    def validate_gender(cls, value: str) -> str:
        value = value.strip().lower()
        if value not in {"all", "male", "female", "other"}:
            raise ValueError("Gender must be 'all', 'male', 'female', or 'other'")
        return value


class ParameterReferenceRangeCreate(ParameterReferenceRangeBase):
    pass


class ParameterReferenceRangeUpdate(BaseModel):
    gender: str | None = Field(default=None, max_length=20)
    min_age_days: int | None = Field(default=None, ge=0)
    max_age_days: int | None = Field(default=None, ge=0)
    age_group_label: str | None = Field(default=None, max_length=100)
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    normal_range_text: str | None = Field(default=None, max_length=255)
    notes: str | None = None
    is_active: bool | None = None

    @field_validator("gender")
    @classmethod
    def validate_update_gender(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip().lower()
        if value not in {"all", "male", "female", "other"}:
            raise ValueError("Gender must be 'all', 'male', 'female', or 'other'")
        return value


class ParameterReferenceRangeRead(ParameterReferenceRangeBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    parameter_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ============================================================
# FORMULA AND COPY SCHEMAS
# ============================================================

class FormulaValidationRequest(BaseModel):
    formula: str = Field(..., min_length=1, max_length=255)
    test_case_id: int = Field(..., gt=0)


class FormulaValidationResponse(BaseModel):
    is_valid: bool
    variables: list[str]
    missing_variables: list[str]
    message: str


class CopyParametersRequest(BaseModel):
    overwrite_existing: bool = False


class CopyParametersResponse(BaseModel):
    copied_count: int
    skipped_count: int
    parameters: list[TestParameterRead]