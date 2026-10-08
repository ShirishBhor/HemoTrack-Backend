from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate


def get_doctor(db: Session, doctor_id: int) -> Doctor | None:
    return db.get(Doctor, doctor_id)


def get_doctor_or_404(db: Session, doctor_id: int) -> Doctor:
    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Return a clear 404 response when a doctor does not exist.
    doctor = get_doctor(db, doctor_id)

    if doctor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found",
        )

    return doctor


def list_doctors(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    active_only: bool = True,
) -> list[Doctor]:
    query = select(Doctor)

    if active_only:
        query = query.where(Doctor.is_active.is_(True))

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


# Changes by Nikhil Mole | 2026-10-01
# Reason: Add a dedicated search service for doctor name, phone, and specialization.
def search_doctors(
    db: Session,
    *,
    search: str,
    skip: int = 0,
    limit: int = 50,
    active_only: bool = True,
) -> list[Doctor]:
    term = search.strip()

    if not term:
        return []

    pattern = f"%{term.lower()}%"

    query = select(Doctor).where(
        or_(
            func.lower(Doctor.name).like(pattern),
            func.lower(Doctor.phone).like(pattern),
            func.lower(Doctor.specialization).like(pattern),
        )
    )

    if active_only:
        query = query.where(Doctor.is_active.is_(True))

    query = query.order_by(Doctor.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


# Changes by Nikhil Mole | 2026-10-01
# Reason: Validate email and phone uniqueness before writing doctor data.
def _validate_doctor_uniqueness(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    doctor_id: int | None = None,
) -> None:
    if email is not None:
        email_query = select(Doctor).where(
            func.lower(Doctor.email) == email.lower()
        )

        if doctor_id is not None:
            email_query = email_query.where(Doctor.id != doctor_id)

        existing_email = db.scalar(email_query)

        if existing_email is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor with this email already exists",
            )

    if phone is not None:
        phone_query = select(Doctor).where(
            Doctor.phone == phone
        )

        if doctor_id is not None:
            phone_query = phone_query.where(Doctor.id != doctor_id)

        existing_phone = db.scalar(phone_query)

        if existing_phone is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Doctor with this phone number already exists",
            )


# Changes by Nikhil Mole | 2026-10-01
# Reason: Handle database errors and roll back failed transactions.
def _commit_doctor_changes(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Doctor data conflicts with an existing database record",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save doctor data",
        ) from exc


def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    doctor_data = payload.model_dump()

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Prevent duplicate doctor email and phone records.
    _validate_doctor_uniqueness(
        db,
        email=doctor_data.get("email"),
        phone=doctor_data.get("phone"),
    )

    doctor = Doctor(**doctor_data)
    db.add(doctor)

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Centralize commit and rollback handling for doctor creation.
    _commit_doctor_changes(db)

    try:
        db.refresh(doctor)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load the created doctor",
        ) from exc

    return doctor


def update_doctor(
    db: Session,
    doctor: Doctor,
    payload: DoctorUpdate,
) -> Doctor:
    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Update only fields explicitly provided in the PATCH request.
    update_data = payload.model_dump(exclude_unset=True)

    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Prevent duplicate email and phone while allowing
    # the current doctor to keep their own existing values.
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

    try:
        db.refresh(doctor)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load the updated doctor",
        ) from exc

    return doctor


def deactivate_doctor(db: Session, doctor: Doctor) -> Doctor:
    # Changes by Nikhil Mole | 2026-10-01
    # Reason: Deactivate doctors without permanently deleting their records.
    doctor.is_active = False
    db.add(doctor)
    _commit_doctor_changes(db)

    try:
        db.refresh(doctor)
    except SQLAlchemyError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to load the deactivated doctor",
        ) from exc

    return doctor
