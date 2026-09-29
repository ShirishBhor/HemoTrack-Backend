import enum
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
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


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    gender: Mapped[Gender] = mapped_column(
        Enum(Gender, name="gender", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
    )
    age_years: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_months: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    patient_type: Mapped[PatientType] = mapped_column(
        Enum(PatientType, name="patient_type", values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=PatientType.OTHER,
    )
    phone: Mapped[str | None] = mapped_column(String(30), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    collection_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    received_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    reporting_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    referred_by_doctor_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("doctors.id"),
        nullable=True,
        index=True,
    )
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
