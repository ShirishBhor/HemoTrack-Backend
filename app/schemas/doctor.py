from datetime import datetime
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


class _DoctorValidators(BaseModel):
    """
    Shared field validators for Doctor schemas.
    Both DoctorBase and DoctorUpdate inherit from this mixin
    to avoid duplicating validator logic.
    """

    @field_validator("name", check_fields=False)
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Doctor name must not be blank")
        return value

    @field_validator("specialization", "clinic_address", check_fields=False)
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


class DoctorBase(_DoctorValidators):
    name: str = Field(min_length=1, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    clinic_address: str | None = Field(default=None, max_length=2000)


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(_DoctorValidators):
    """
    Partial update schema for doctors.

    All fields are optional (PATCH semantics).
    is_active is intentionally excluded — use the dedicated
    /deactivate and /reactivate endpoints to control it.
    """

    name: str | None = Field(default=None, min_length=1, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    clinic_address: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_update(self) -> "DoctorUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Doctor name cannot be set to null")
        return self


class DoctorRead(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime


class DoctorListResponse(BaseModel):
    """Paginated doctor list with total count for frontend pagination UI."""

    total: int
    items: list[DoctorRead]
