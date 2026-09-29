from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate


def get_doctor(db: Session, doctor_id: int) -> Doctor | None:
    return db.get(Doctor, doctor_id)


def get_doctor_or_404(db: Session, doctor_id: int) -> Doctor:
    doctor = get_doctor(db, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
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
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Doctor.name).like(pattern),
                func.lower(Doctor.specialization).like(pattern),
                func.lower(Doctor.phone).like(pattern),
            )
        )
    query = query.order_by(Doctor.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def create_doctor(db: Session, payload: DoctorCreate) -> Doctor:
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def update_doctor(db: Session, doctor: Doctor, payload: DoctorUpdate) -> Doctor:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor


def deactivate_doctor(db: Session, doctor: Doctor) -> Doctor:
    doctor.is_active = False
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    return doctor
