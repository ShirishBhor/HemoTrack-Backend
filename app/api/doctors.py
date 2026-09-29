from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.doctor import DoctorCreate, DoctorRead, DoctorUpdate
from app.services import doctor_service

router = APIRouter(prefix="/doctors", tags=["doctors"])

DoctorWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]

DoctorManageUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
]


@router.get("", response_model=list[DoctorRead])
def list_doctors(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
    active_only: bool = Query(default=True),
):
    return doctor_service.list_doctors(
        db,
        skip=skip,
        limit=limit,
        search=search,
        active_only=active_only,
    )


@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(
    payload: DoctorCreate,
    db: DbSession,
    _: DoctorWriteUser,
):
    return doctor_service.create_doctor(db, payload)


@router.get("/{doctor_id}", response_model=DoctorRead)
def get_doctor(
    doctor_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return doctor_service.get_doctor_or_404(db, doctor_id)


@router.patch("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    doctor_id: int,
    payload: DoctorUpdate,
    db: DbSession,
    _: DoctorWriteUser,
):
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    return doctor_service.update_doctor(db, doctor, payload)


@router.delete("/{doctor_id}", response_model=DoctorRead)
def deactivate_doctor(
    doctor_id: int,
    db: DbSession,
    _: DoctorManageUser,
):
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    return doctor_service.deactivate_doctor(db, doctor)
