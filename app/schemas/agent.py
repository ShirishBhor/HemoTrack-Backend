"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
Pydantic schemas for Agent management.
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

from app.schemas.collection_center import CommissionBillItem


class _AgentValidators(BaseModel):
    """Shared field validators for Agent schemas."""

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Agent name must not be blank")
        return value

    @field_validator("address", check_fields=False)
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


class AgentBase(_AgentValidators):
    name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)


class AgentCreate(AgentBase):
    pass


class AgentUpdate(_AgentValidators):
    """
    Partial update schema for agents.
    All fields are optional (PATCH semantics).
    is_active is intentionally excluded — use dedicated /deactivate and /reactivate endpoints.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    address: str | None = Field(default=None, max_length=2000)
    commission_percent: Decimal | None = Field(default=None, ge=0, le=100)

    @model_validator(mode="after")
    def validate_update(self) -> "AgentUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Agent name cannot be set to null")
        return self


class AgentRead(AgentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    """Paginated agent list with total count."""

    total: int
    items: list[AgentRead]


class AgentStatsResponse(BaseModel):
    """Statistics, revenue, and earned commission for an agent."""

    agent_id: int
    agent_name: str
    commission_percent: Decimal
    total_patients: int
    total_bills: int
    total_billed_amount: Decimal
    total_paid_amount: Decimal
    total_commission_earned: Decimal
    recent_bills: list[CommissionBillItem]

