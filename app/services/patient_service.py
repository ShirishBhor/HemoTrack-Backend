from calendar import monthrange
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload

from app.models.agent import Agent
from app.models.collection_center import CollectionCenter
from app.models.doctor import Doctor
from app.models.patient import Patient, PatientType
from app.schemas.patient import PatientCreate, PatientUpdate


def calculate_age_from_dob(dob: date) -> tuple[int, int, int]:
    today = date.today()
    if dob > today:
        return 0, 0, 0
    years = today.year - dob.year
    months = today.month - dob.month
    days = today.day - dob.day

    if days < 0:
        months -= 1
        prev_month = (today.month - 1) or 12
        prev_year = today.year if today.month > 1 else today.year - 1
        _, days_in_prev_month = monthrange(prev_year, prev_month)
        days += days_in_prev_month

    if months < 0:
        years -= 1
        months += 12

    return max(0, years), max(0, months), max(0, days)


def generate_uhid(db: Session) -> str:
    current_year = date.today().year
    prefix = f"HT-{current_year}-"
    latest_patient = db.scalar(
        select(Patient)
        .where(Patient.uhid.like(f"{prefix}%"))
        .order_by(Patient.id.desc())
        .limit(1)
    )
    if latest_patient and latest_patient.uhid.startswith(prefix):
        try:
            seq_num = int(latest_patient.uhid.split("-")[-1]) + 1
        except ValueError:
            seq_num = db.scalar(select(func.count(Patient.id))) + 1
    else:
        seq_num = db.scalar(select(func.count(Patient.id))) + 1

    return f"{prefix}{seq_num:05d}"


def get_patient(db: Session, patient_id: int) -> Patient | None:
    return db.scalar(
        select(Patient)
        .options(
            joinedload(Patient.referred_by_doctor),
            joinedload(Patient.collection_center),
            joinedload(Patient.agent),
        )
        .where(Patient.id == patient_id)
    )


def get_patient_by_uhid(db: Session, uhid: str) -> Patient | None:
    return db.scalar(
        select(Patient)
        .options(
            joinedload(Patient.referred_by_doctor),
            joinedload(Patient.collection_center),
            joinedload(Patient.agent),
        )
        .where(Patient.uhid == uhid)
    )


def get_patient_by_barcode(db: Session, barcode: str) -> Patient | None:
    return db.scalar(
        select(Patient)
        .options(
            joinedload(Patient.referred_by_doctor),
            joinedload(Patient.collection_center),
            joinedload(Patient.agent),
        )
        .where(Patient.sample_barcode == barcode)
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


def _validate_collection_center_ref(db: Session, collection_center_id: int | None) -> None:
    if collection_center_id is None:
        return
    center = db.get(CollectionCenter, collection_center_id)
    if center is None or not center.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection center not found or inactive",
        )


def _validate_agent_ref(db: Session, agent_id: int | None) -> None:
    if agent_id is None:
        return
    agent = db.get(Agent, agent_id)
    if agent is None or not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent not found or inactive",
        )


def list_patients(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    patient_type: PatientType | None = None,
    doctor_id: int | None = None,
    collection_center_id: int | None = None,
    agent_id: int | None = None,
    collection_date: date | None = None,
    include_cancelled: bool = False,
) -> list[Patient]:
    query = select(Patient).options(
        joinedload(Patient.referred_by_doctor),
        joinedload(Patient.collection_center),
        joinedload(Patient.agent),
    )
    if not include_cancelled:
        query = query.where(Patient.is_cancelled.is_(False), Patient.is_active.is_(True))
    if search:
        pattern = f"%{search.lower()}%"
        query = query.where(
            or_(
                func.lower(Patient.name).like(pattern),
                func.lower(Patient.phone).like(pattern),
                func.lower(Patient.email).like(pattern),
                func.lower(Patient.uhid).like(pattern),
                func.lower(Patient.national_id).like(pattern),
                func.lower(Patient.sample_barcode).like(pattern),
            )
        )
    if patient_type is not None:
        query = query.where(Patient.patient_type == patient_type)
    if doctor_id is not None:
        query = query.where(Patient.referred_by_doctor_id == doctor_id)
    if collection_center_id is not None:
        query = query.where(Patient.collection_center_id == collection_center_id)
    if agent_id is not None:
        query = query.where(Patient.agent_id == agent_id)
    if collection_date is not None:
        query = query.where(Patient.collection_date == collection_date)
    query = query.order_by(Patient.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(query).unique().all())


def create_patient(db: Session, payload: PatientCreate, created_by: int | None) -> Patient:
    _validate_doctor_ref(db, payload.referred_by_doctor_id)
    _validate_collection_center_ref(db, payload.collection_center_id)
    _validate_agent_ref(db, payload.agent_id)
    data = payload.model_dump()
    if not data.get("uhid"):
        data["uhid"] = generate_uhid(db)
    else:
        existing = get_patient_by_uhid(db, data["uhid"])
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="UHID already registered",
            )

    if data.get("dob"):
        years, months, days = calculate_age_from_dob(data["dob"])
        data["age_years"] = years
        data["age_months"] = months
        data["age_days"] = days

    patient = Patient(**data, created_by=created_by)
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return get_patient_or_404(db, patient.id)


def update_patient(db: Session, patient: Patient, payload: PatientUpdate) -> Patient:
    data = payload.model_dump(exclude_unset=True)
    if "referred_by_doctor_id" in data:
        _validate_doctor_ref(db, data["referred_by_doctor_id"])
    if "collection_center_id" in data:
        _validate_collection_center_ref(db, data["collection_center_id"])
    if "agent_id" in data:
        _validate_agent_ref(db, data["agent_id"])
    if "uhid" in data and data["uhid"] != patient.uhid:
        if data["uhid"]:
            existing = get_patient_by_uhid(db, data["uhid"])
            if existing and existing.id != patient.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="UHID already registered",
                )
    if "dob" in data and data["dob"]:
        years, months, days = calculate_age_from_dob(data["dob"])
        data["age_years"] = years
        data["age_months"] = months
        data["age_days"] = days

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

