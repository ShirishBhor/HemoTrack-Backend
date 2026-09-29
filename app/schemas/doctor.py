from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class DoctorBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    clinic_address: str | None = None


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    specialization: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    clinic_address: str | None = None
    is_active: bool | None = None


class DoctorRead(DoctorBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
