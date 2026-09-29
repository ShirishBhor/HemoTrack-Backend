from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.patient import PatientType
from app.models.user import User, UserRole
from app.schemas.patient import PatientCreate, PatientRead, PatientUpdate
from app.services import patient_service

router = APIRouter(prefix="/patients", tags=["patients"])

PatientWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]


@router.get("", response_model=list[PatientRead])
def list_patients(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
    patient_type: PatientType | None = None,
    doctor_id: int | None = None,
    collection_date: date | None = None,
    include_cancelled: bool = Query(default=False),
):
    return patient_service.list_patients(
        db,
        skip=skip,
        limit=limit,
        search=search,
        patient_type=patient_type,
        doctor_id=doctor_id,
        collection_date=collection_date,
        include_cancelled=include_cancelled,
    )


@router.post("", response_model=PatientRead, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload: PatientCreate,
    db: DbSession,
    current_user: PatientWriteUser,
):
    return patient_service.create_patient(db, payload, created_by=current_user.id)


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(
    patient_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return patient_service.get_patient_or_404(db, patient_id)


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(
    patient_id: int,
    payload: PatientUpdate,
    db: DbSession,
    _: PatientWriteUser,
):
    patient = patient_service.get_patient_or_404(db, patient_id)
    return patient_service.update_patient(db, patient, payload)


@router.post("/{patient_id}/cancel", response_model=PatientRead)
def cancel_patient(
    patient_id: int,
    db: DbSession,
    _: PatientWriteUser,
):
    patient = patient_service.get_patient_or_404(db, patient_id)
    return patient_service.cancel_patient(db, patient)
