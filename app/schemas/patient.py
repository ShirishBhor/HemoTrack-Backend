from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.patient import Gender, PatientType
from app.schemas.doctor import DoctorRead


class PatientBase(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    gender: Gender
    age_years: int = Field(default=0, ge=0, le=150)
    age_months: int = Field(default=0, ge=0, le=11)
    age_days: int = Field(default=0, ge=0, le=31)
    patient_type: PatientType = PatientType.OTHER
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    collection_date: date | None = None
    received_date: date | None = None
    reporting_date: date | None = None
    referred_by_doctor_id: int | None = None
    agent_or_collection_centre: str | None = Field(default=None, max_length=255)
    remarks: str | None = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    gender: Gender | None = None
    age_years: int | None = Field(default=None, ge=0, le=150)
    age_months: int | None = Field(default=None, ge=0, le=11)
    age_days: int | None = Field(default=None, ge=0, le=31)
    patient_type: PatientType | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    collection_date: date | None = None
    received_date: date | None = None
    reporting_date: date | None = None
    referred_by_doctor_id: int | None = None
    agent_or_collection_centre: str | None = Field(default=None, max_length=255)
    remarks: str | None = None
    is_active: bool | None = None


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    is_cancelled: bool
    is_active: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    referred_by_doctor: DoctorRead | None = None
