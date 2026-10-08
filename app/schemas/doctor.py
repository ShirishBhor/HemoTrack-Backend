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


# Changes by Nikhil Mole | 2026-10-01
# Reason: Define Indian mobile number format for consistent validation.
# Indian mobile numbers must contain exactly 10 digits
_PHONE_PATTERN = re.compile(r"^[6-9]\d{9}$")


class DoctorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, min_length=10, max_length=10)
    email: EmailStr | None = None
    clinic_address: str | None = Field(default=None, max_length=2000)

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Trim whitespace and reject blank doctor names.
    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Doctor name must not be blank")

        return value

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Normalize optional text fields before saving.
    @field_validator("specialization", "phone", "clinic_address")
    @classmethod
    def normalize_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Validate Indian mobile numbers.
    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not _PHONE_PATTERN.fullmatch(value):
            raise ValueError(
                "Phone must be a valid 10-digit Indian mobile number "
                "starting with 6, 7, 8, or 9"
            )

        return value

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Normalize email addresses for consistent storage.
    @field_validator("email")
    @classmethod
    def normalize_email(
        cls,
        value: EmailStr | None,
    ) -> EmailStr | None:
        if value is None:
            return None

        return str(value).strip().lower()


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=255,
    )
    specialization: str | None = Field(
        default=None,
        max_length=255,
    )
    phone: str | None = Field(
        default=None,
        min_length=10,
        max_length=10,
    )
    email: EmailStr | None = None
    clinic_address: str | None = Field(
        default=None,
        max_length=2000,
    )
    is_active: bool | None = None

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Reject empty PATCH requests and prevent a null required name.
    @model_validator(mode="after")
    def validate_update(self):
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")

        if "name" in self.model_fields_set and self.name is None:
            raise ValueError("Doctor name cannot be null")

        return self

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Ensure an updated doctor name is not blank.
    @field_validator("name")
    @classmethod
    def validate_update_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError("Doctor name must not be blank")

        return value

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Normalize optional fields during partial updates.
    @field_validator("specialization", "phone", "clinic_address")
    @classmethod
    def normalize_update_optional_text(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Apply Indian mobile number validation to partial updates.
    @field_validator("phone")
    @classmethod
    def validate_update_phone(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if not _PHONE_PATTERN.fullmatch(value):
            raise ValueError(
                "Phone must be a valid 10-digit Indian mobile number "
                "starting with 6, 7, 8, or 9"
            )

        return value

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Keep updated email addresses in a consistent format.
    @field_validator("email")
    @classmethod
    def normalize_update_email(
        cls,
        value: EmailStr | None,
    ) -> EmailStr | None:
        if value is None:
            return None

        return str(value).strip().lower()


class DoctorRead(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
