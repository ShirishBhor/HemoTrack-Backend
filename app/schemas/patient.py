from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.models.patient import BloodGroup, Gender, MaritalStatus, PatientType
from app.schemas.agent import AgentRead
from app.schemas.collection_center import CollectionCenterRead
from app.schemas.doctor import DoctorRead


class PatientBase(BaseModel):
    uhid: str | None = Field(default=None, max_length=50)
    name: str = Field(min_length=1, max_length=255)
    gender: Gender
    dob: date | None = None
    age_years: int = Field(default=0, ge=0, le=150)
    age_months: int = Field(default=0, ge=0, le=11)
    age_days: int = Field(default=0, ge=0, le=31)
    blood_group: BloodGroup = BloodGroup.UNKNOWN
    patient_type: PatientType = PatientType.OTHER
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    national_id: str | None = Field(default=None, max_length=50)
    marital_status: MaritalStatus | None = None
    guardian_name: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    relationship_to_patient: str | None = Field(default=None, max_length=50)
    collection_date: date | None = None
    received_date: date | None = None
    reporting_date: date | None = None
    sample_barcode: str | None = Field(default=None, max_length=100)
    referred_by_doctor_id: int | None = None
    collection_center_id: int | None = None
    agent_id: int | None = None
    agent_or_collection_centre: str | None = Field(default=None, max_length=255)
    remarks: str | None = None

    @field_validator("dob")
    @classmethod
    def validate_dob(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @model_validator(mode="after")
    def validate_date_sequence(self) -> "PatientBase":
        c_date = self.collection_date
        rec_date = self.received_date
        rep_date = self.reporting_date

        if c_date and rec_date and c_date > rec_date:
            raise ValueError("collection_date must be less than or equal to received_date")
        if rec_date and rep_date and rec_date > rep_date:
            raise ValueError("received_date must be less than or equal to reporting_date")
        if c_date and rep_date and c_date > rep_date:
            raise ValueError("collection_date must be less than or equal to reporting_date")
        return self


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    uhid: str | None = Field(default=None, max_length=50)
    name: str | None = Field(default=None, min_length=1, max_length=255)
    gender: Gender | None = None
    dob: date | None = None
    age_years: int | None = Field(default=None, ge=0, le=150)
    age_months: int | None = Field(default=None, ge=0, le=11)
    age_days: int | None = Field(default=None, ge=0, le=31)
    blood_group: BloodGroup | None = None
    patient_type: PatientType | None = None
    phone: str | None = Field(default=None, max_length=30)
    email: EmailStr | None = None
    address: str | None = None
    national_id: str | None = Field(default=None, max_length=50)
    marital_status: MaritalStatus | None = None
    guardian_name: str | None = Field(default=None, max_length=255)
    emergency_contact_name: str | None = Field(default=None, max_length=255)
    emergency_contact_phone: str | None = Field(default=None, max_length=30)
    relationship_to_patient: str | None = Field(default=None, max_length=50)
    collection_date: date | None = None
    received_date: date | None = None
    reporting_date: date | None = None
    sample_barcode: str | None = Field(default=None, max_length=100)
    referred_by_doctor_id: int | None = None
    collection_center_id: int | None = None
    agent_id: int | None = None
    agent_or_collection_centre: str | None = Field(default=None, max_length=255)
    remarks: str | None = None
    is_active: bool | None = None

    @field_validator("dob")
    @classmethod
    def validate_dob(cls, v: date | None) -> date | None:
        if v is not None and v > date.today():
            raise ValueError("Date of birth cannot be in the future")
        return v

    @model_validator(mode="after")
    def validate_date_sequence(self) -> "PatientUpdate":
        c_date = self.collection_date
        rec_date = self.received_date
        rep_date = self.reporting_date

        if c_date and rec_date and c_date > rec_date:
            raise ValueError("collection_date must be less than or equal to received_date")
        if rec_date and rep_date and rec_date > rep_date:
            raise ValueError("received_date must be less than or equal to reporting_date")
        if c_date and rep_date and c_date > rep_date:
            raise ValueError("collection_date must be less than or equal to reporting_date")
        return self


class PatientRead(PatientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    uhid: str
    is_cancelled: bool
    is_active: bool
    created_by: int | None
    created_at: datetime
    updated_at: datetime
    referred_by_doctor: DoctorRead | None = None
    collection_center: CollectionCenterRead | None = None
    agent: AgentRead | None = None

