import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

from app.models.user import UserRole


def _clean_employee_code(v: str | None) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip().upper()
        if not v:
            return None
        if not re.match(r"^[A-Z0-9\-_]{3,50}$", v):
            raise ValueError("employee_code must be 3-50 alphanumeric characters, hyphens, or underscores")
        return v
    return v


def _clean_department(v: str | None) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    return v


def _clean_url(v: str | None) -> str | None:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        if not v:
            return None
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("profile_picture_url must start with http:// or https://")
        return v
    return v


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    role: UserRole = UserRole.RECEPTIONIST
    employee_code: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)
    profile_picture_url: str | None = Field(default=None, max_length=500)

    @field_validator("employee_code", mode="before")
    @classmethod
    def validate_employee_code(cls, v: str | None) -> str | None:
        return _clean_employee_code(v)

    @field_validator("department", mode="before")
    @classmethod
    def validate_department(cls, v: str | None) -> str | None:
        return _clean_department(v)

    @field_validator("profile_picture_url", mode="before")
    @classmethod
    def validate_profile_picture_url(cls, v: str | None) -> str | None:
        return _clean_url(v)


class UserCreate(UserBase):
    password: str = Field(min_length=8, max_length=128)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    role: UserRole | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)
    is_active: bool | None = None
    employee_code: str | None = Field(default=None, max_length=50)
    department: str | None = Field(default=None, max_length=100)
    profile_picture_url: str | None = Field(default=None, max_length=500)

    @field_validator("employee_code", mode="before")
    @classmethod
    def validate_employee_code(cls, v: str | None) -> str | None:
        return _clean_employee_code(v)

    @field_validator("department", mode="before")
    @classmethod
    def validate_department(cls, v: str | None) -> str | None:
        return _clean_department(v)

    @field_validator("profile_picture_url", mode="before")
    @classmethod
    def validate_profile_picture_url(cls, v: str | None) -> str | None:
        return _clean_url(v)


class UserRead(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    last_login_at: datetime | None = None
    failed_login_attempts: int = 0
    is_locked: bool = False
    created_at: datetime
    updated_at: datetime


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
