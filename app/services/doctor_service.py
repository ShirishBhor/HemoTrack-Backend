"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
Business logic for Doctor management.

Handles:
- Listing and searching doctors
- Creating, updating, deactivating, and reactivating doctors
- Uniqueness validation for email and phone
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate

logger = logging.getLogger(__name__)


def get_doctor(db: Session, doctor_id: int) -> Doctor | None:
    return db.get(Doctor, doctor_id)


def get_doctor_or_404(db: Session, doctor_id: int) -> Doctor:
    doctor = get_doctor(db, doctor_id)
    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )
    return doctor


def count_doctors(
    db: Session,
    *,
    search: str | None = None,
    is_active: bool | None = None,
) -> int:
    """Return the total number of doctors matching the given filters."""
    query = select(func.count(Doctor.id))

    if isinstance(is_active, bool):
        query = query.where(Doctor.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Doctor.name).like(pattern),
                func.lower(Doctor.specialization).like(pattern),
                func.lower(Doctor.phone).like(pattern),
            )
        )

    return db.scalar(query) or 0


def list_doctors(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Doctor]:
    query = select(Doctor)

    if isinstance(is_active, bool):
        query = query.where(Doctor.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Doctor.name).like(pattern),
                func.lower(Doctor.specialization).like(pattern),
                func.lower(Doctor.phone).like(pattern),
            )
        )

    query = query.order_by(Doctor.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def _validate_doctor_uniqueness(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    doctor_id: int | None = None,
) -> None:
    """Raise 409 if email or phone is already taken by another doctor."""
    if email is not None:
        email_query = select(Doctor).where(
            func.lower(Doctor.email) == email.lower()
        )
        if doctor_id is not None:
            email_query = email_query.where(Doctor.id != doctor_id)
        if db.scalar(email_query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor with this email already exists",
            )

    if phone is not None:
        phone_query = select(Doctor).where(Doctor.phone == phone)
        if doctor_id is not None:
            phone_query = phone_query.where(Doctor.id != doctor_id)
        if db.scalar(phone_query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor with this phone number already exists",
            )


def _commit_doctor_changes(db: Session) -> None:
    """Commit the session, rolling back and raising on DB errors."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error("Doctor integrity error on commit", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor data conflicts with an existing database record",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Doctor database error on commit", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save doctor data",
        ) from exc


def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    doctor_data = payload.model_dump()

    _validate_doctor_uniqueness(
        db,
        email=doctor_data.get("email"),
        phone=doctor_data.get("phone"),
    )

    doctor = Doctor(**doctor_data)
    db.add(doctor)
    _commit_doctor_changes(db)
    db.refresh(doctor)
    return doctor


def update_doctor(
    db: Session,
    doctor: Doctor,
    payload: DoctorUpdate,
) -> Doctor:
    update_data = payload.model_dump(exclude_unset=True)

    _validate_doctor_uniqueness(
        db,
        email=update_data.get("email"),
        phone=update_data.get("phone"),
        doctor_id=doctor.id,
    )

    for field, value in update_data.items():
        setattr(doctor, field, value)

    db.add(doctor)
    _commit_doctor_changes(db)
    db.refresh(doctor)
    return doctor


def update_doctor_status(db: Session, doctor: Doctor, is_active: bool) -> Doctor:
    """Activate or deactivate a doctor."""
    if is_active:
        return reactivate_doctor(db, doctor)
    return deactivate_doctor(db, doctor)


def deactivate_doctor(db: Session, doctor: Doctor) -> Doctor:
    """Soft-delete a doctor by setting is_active = False."""
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor is already inactive",
        )

    doctor.is_active = False
    db.add(doctor)
    _commit_doctor_changes(db)
    db.refresh(doctor)
    return doctor


def reactivate_doctor(db: Session, doctor: Doctor) -> Doctor:
    """Restore a previously deactivated doctor."""
    if doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Doctor is already active",
        )

    doctor.is_active = True
    db.add(doctor)
    _commit_doctor_changes(db)
    db.refresh(doctor)
    return doctor
