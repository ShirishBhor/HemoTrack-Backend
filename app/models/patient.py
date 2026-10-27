import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PatientType(str, enum.Enum):
    OTHER = "OTHER"
    OPD = "OPD"
    IPD = "IPD"


class Gender(str, enum.Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"


class BloodGroup(str, enum.Enum):
    A_POSITIVE = "A+"
    A_NEGATIVE = "A-"
    B_POSITIVE = "B+"
    B_NEGATIVE = "B-"
    AB_POSITIVE = "AB+"
    AB_NEGATIVE = "AB-"
    O_POSITIVE = "O+"
    O_NEGATIVE = "O-"
    UNKNOWN = "UNKNOWN"


class MaritalStatus(str, enum.Enum):
    SINGLE = "SINGLE"
    MARRIED = "MARRIED"
    DIVORCED = "DIVORCED"
    WIDOWED = "WIDOWED"
    OTHER = "OTHER"


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    uhid: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    age_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blood_group: Mapped[BloodGroup] = mapped_column(
        Enum(BloodGroup, name="blood_group", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=BloodGroup.UNKNOWN,
    )
    patient_type: Mapped[PatientType] = mapped_column(
        Enum(PatientType, name="patient_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PatientType.OTHER,
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    national_id: Mapped[str | None] = mapped_column(String(50), index=True, nullable=True)
    marital_status: Mapped[MaritalStatus | None] = mapped_column(
        Enum(MaritalStatus, name="marital_status", values_callable=lambda x: [e.value for e in x]),
        nullable=True,
    )
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    emergency_contact_phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    relationship_to_patient: Mapped[str | None] = mapped_column(String(50), nullable=True)
    collection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reporting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    sample_barcode: Mapped[str | None] = mapped_column(String(100), index=True, nullable=True)
    referred_by_doctor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=True,
        index=True,
    )
    # Structured FK references
    collection_center_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("collection_centers.id"),
        nullable=True,
        index=True,
    )

    agent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("agents.id"),
        nullable=True,
        index=True,
    )
    # Legacy text field for backward compatibility
    agent_or_collection_centre: Mapped[str | None] = mapped_column(String(255), nullable=True)
    remarks: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_cancelled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_by: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    referred_by_doctor = relationship("Doctor", back_populates="patients")
    created_by_user = relationship("User", back_populates="patients_created")
    collection_center = relationship(
        "CollectionCenter",
        back_populates="patients",
        foreign_keys=[collection_center_id],
    )
    agent = relationship(
        "Agent",
        back_populates="patients",
        foreign_keys=[agent_id],
    )

