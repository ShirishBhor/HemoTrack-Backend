from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.doctor import Doctor
from app.models.patient import Patient, PatientType
from app.schemas.patient import PatientCreate, PatientUpdate


def get_patient(db: Session, patient_id: int) -> Patient | None:
    return db.scalar(
        select(Patient)
        .options(joinedload(Patient.referred_by_doctor))
        .where(Patient.id == patient_id)
    )


def get_patient_or_404(db: Session, patient_id: int) -> Patient:
    patient = get_patient(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


def _validate_doctor_ref(db: Session, doctor_id: int | None) -> None:
    if doctor_id is None:
        return
    doctor = db.get(Doctor, doctor_id)
    if doctor is None or not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Referred doctor not found or inactive",
        )


def list_patients(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    patient_type: PatientType | None = None,
    doctor_id: int | None = None,
    collection_date: date | None = None,
    include_cancelled: bool = False,
) -> list[Patient]:
    query = select(Patient).options(joinedload(Patient.referred_by_doctor))
    if not include_cancelled:
        query = query.where(Patient.is_cancelled.is_(False), Patient.is_active.is_(True))
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(func.lower(Patient.name).like(pattern))
    if patient_type is not None:
        query = query.where(Patient.patient_type == patient_type)
    if doctor_id is not None:
        query = query.where(Patient.referred_by_doctor_id == doctor_id)
    if collection_date is not None:
        query = query.where(Patient.collection_date == collection_date)
    query = query.order_by(Patient.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(query).unique().all())


def create_patient(db: Session, payload: PatientCreate, created_by: int | None) -> Patient:
    _validate_doctor_ref(db, payload.referred_by_doctor_id)
    patient = Patient(**payload.model_dump(), created_by=created_by)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return get_patient_or_404(db, patient.id)


def update_patient(db: Session, patient: Patient, payload: PatientUpdate) -> Patient:
    data = payload.model_dump(exclude_unset=True)
    if "referred_by_doctor_id" in data:
        _validate_doctor_ref(db, data["referred_by_doctor_id"])
    for field, value in data.items():
        setattr(patient, field, value)
    db.add(patient)
    db.commit()
    return get_patient_or_404(db, patient.id)


def cancel_patient(db: Session, patient: Patient) -> Patient:
    patient.is_cancelled = True
    patient.is_active = False
    db.add(patient)
    db.commit()
    return get_patient_or_404(db, patient.id)
