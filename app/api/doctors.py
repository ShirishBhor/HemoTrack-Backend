"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
API router for Doctor management.

Available operations:
- GET    /doctors                      — List all doctors (paginated + search)
- POST   /doctors                      — Create a new doctor
- GET    /doctors/{id}                 — Get a doctor by ID
- PATCH  /doctors/{id}                 — Update a doctor
- PATCH  /doctors/{id}/status             — Activate or deactivate a doctor
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.common import StatusUpdate
from app.schemas.doctor import DoctorCreate, DoctorListResponse, DoctorRead, DoctorUpdate
from app.services import doctor_service


router = APIRouter(prefix="/doctors", tags=["doctors"])


# ============================================================
# PERMISSION GROUPS
# ============================================================

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


# ============================================================
# LIST DOCTORS
# ============================================================

@router.get("", response_model=DoctorListResponse)
def list_doctors(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of records to return",
    ),
    search: str | None = Query(
        default=None,
        max_length=255,
        description="Search by name, phone, or specialization",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true for active doctors, false for inactive doctors)",
    ),
):
    """
    List doctors with pagination and optional search.

    Returns total count alongside items so clients can build
    pagination controls without a separate request.
    """
    total = doctor_service.count_doctors(
        db,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )
    items = doctor_service.list_doctors(
        db,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )
    return DoctorListResponse(total=total, items=items)


# ============================================================
# CREATE DOCTOR
# ============================================================

@router.post("", response_model=DoctorRead, status_code=status.HTTP_201_CREATED)
def create_doctor(
    payload: DoctorCreate,
    db: DbSession,
    _: DoctorWriteUser,
):
    """
    Create a new doctor.

    Only ADMIN, LAB_MANAGER, and RECEPTIONIST can create doctors.
    """
    return doctor_service.create_doctor(db, payload)


# ============================================================
# GET DOCTOR BY ID
# ============================================================

@router.get("/{doctor_id}", response_model=DoctorRead)
def get_doctor(
    db: DbSession,
    _: CurrentUser,
    doctor_id: int = Path(..., gt=0, description="Doctor ID"),
):
    """
    Get a single doctor by ID.

    Any authenticated user can access this endpoint.
    """
    return doctor_service.get_doctor_or_404(db, doctor_id)


# ============================================================
# UPDATE DOCTOR
# ============================================================

@router.patch("/{doctor_id}", response_model=DoctorRead)
def update_doctor(
    payload: DoctorUpdate,
    db: DbSession,
    _: DoctorWriteUser,
    doctor_id: int = Path(..., gt=0, description="Doctor ID"),
):
    """
    Partially update an existing doctor.

    Only ADMIN, LAB_MANAGER, and RECEPTIONIST can update doctors.
    To change the active status use /status.
    """
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    return doctor_service.update_doctor(db, doctor, payload)


# ============================================================
# UPDATE DOCTOR STATUS
# ============================================================

@router.patch("/{doctor_id}/status", response_model=DoctorRead)
def update_doctor_status(
    payload: StatusUpdate,
    db: DbSession,
    _: DoctorManageUser,
    doctor_id: int = Path(..., gt=0, description="Doctor ID"),
):
    """
    Activate or deactivate a doctor.

    Only ADMIN and LAB_MANAGER can change doctor status.
    """
    doctor = doctor_service.get_doctor_or_404(db, doctor_id)
    return doctor_service.update_doctor_status(db, doctor, payload.is_active)