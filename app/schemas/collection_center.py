"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
Pydantic schemas for Collection Center management.
"""

from datetime import datetime
from decimal import Decimal
import re

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
    field_validator,
    model_validator,
)

# Indian mobile numbers must start with 6-9 and be exactly 10 digits.
_PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")


class _CollectionCenterValidators(BaseModel):
    """Shared field validators for Collection Center schemas."""

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Collection center name must not be blank")
        return value

    @field_validator("address", "contact_person", check_fields=False)
    @classmethod
    def normalize_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip() or None

    @field_validator("phone", check_fields=False)
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not _PHONE_PATTERN.fullmatch(value):
            raise ValueError(
                "Phone must be a valid 10-digit Indian mobile number "
                "starting with 6, 7, 8, or 9"
            )
        return value

    @field_validator("email", check_fields=False)
    @classmethod
    def normalize_email(cls, value: EmailStr | None) -> str | None:
        if value is None:
            return None
        return str(value).strip().lower()

    @field_validator("commission_percent", check_fields=False)
    @classmethod
    def validate_commission_percent(cls, value: Decimal | float | None) -> Decimal | None:
        if value is None:
            return None
        dec_val = Decimal(str(value))
        if dec_val < Decimal("0.00") or dec_val > Decimal("100.00"):
            raise ValueError("Commission percentage must be between 0.00 and 100.00")
        return round(dec_val, 2)


class CollectionCenterBase(_CollectionCenterValidators):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    contact_person: str | None = Field(default=None, max_length=255)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)


class CollectionCenterCreate(CollectionCenterBase):
    pass


class CollectionCenterUpdate(_CollectionCenterValidators):
    """
    Partial update schema for collection centers.
    All fields are optional (PATCH semantics).
    is_active is intentionally excluded — use dedicated /deactivate and /reactivate endpoints.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    contact_person: str | None = Field(default=None, max_length=255)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_update(self) -> "CollectionCenterUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Collection center name cannot be set to null")
        return self


class CollectionCenterRead(CollectionCenterBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class CollectionCenterListResponse(BaseModel):
    """Paginated collection center list with total count."""

    total: int
    items: list[CollectionCenterRead]


class CommissionBillItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    bill_id: int
    bill_number: str
    bill_date: datetime
    patient_id: int
    patient_name: str
    patient_uhid: str
    billed_amount: Decimal
    paid_amount: Decimal
    commission_percent: Decimal
    commission_amount: Decimal
    status: str


class CollectionCenterStatsResponse(BaseModel):
    """Statistics, revenue, and earned commission for a collection center."""

    center_id: int
    center_name: str
    commission_percent: Decimal
    total_patients: int
    total_bills: int
    total_billed_amount: Decimal
    total_paid_amount: Decimal
    total_commission_earned: Decimal
    recent_bills: list[CommissionBillItem]

