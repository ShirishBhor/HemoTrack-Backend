"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
API router for Collection Center management.

Available operations:
- GET    /collection-centers                      — List all collection centers (paginated + search)
- POST   /collection-centers                      — Create a new collection center
- GET    /collection-centers/{id}                 — Get a collection center by ID
- PATCH  /collection-centers/{id}                 — Update a collection center
- PATCH  /collection-centers/{id}/status          — Activate or deactivate a collection center
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.common import StatusUpdate
from app.schemas.collection_center import (
    CollectionCenterCreate,
    CollectionCenterListResponse,
    CollectionCenterRead,
    CollectionCenterStatsResponse,
    CollectionCenterUpdate,
)
from app.schemas.patient import PatientRead
from app.services import collection_center_service, patient_service


router = APIRouter(prefix="/collection-centers", tags=["collection-centers"])


# ============================================================
# PERMISSION GROUPS
# ============================================================

CollectionCenterWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]

CollectionCenterManageUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
]


# ============================================================
# LIST COLLECTION CENTERS
# ============================================================

@router.get("", response_model=CollectionCenterListResponse)
def list_collection_centers(
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
        description="Search by name, contact person, phone, email, or address",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true for active collection centers, false for inactive collection centers)",
    ),
):
    """
    List collection centers with pagination and optional search.

    Returns total count alongside items so clients can build
    pagination controls without a separate request.
    """
    total = collection_center_service.count_collection_centers(
        db,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )
    items = collection_center_service.list_collection_centers(
        db,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )
    return CollectionCenterListResponse(total=total, items=items)


# ============================================================
# CREATE COLLECTION CENTER
# ============================================================

@router.post("", response_model=CollectionCenterRead, status_code=status.HTTP_201_CREATED)
def create_collection_center(
    payload: CollectionCenterCreate,
    db: DbSession,
    _: CollectionCenterWriteUser,
):
    """
    Create a new collection center.

    Only ADMIN, LAB_MANAGER, and RECEPTIONIST can create collection centers.
    """
    return collection_center_service.create_collection_center(db, payload)


# ============================================================
# GET COLLECTION CENTER BY ID
# ============================================================

@router.get("/{center_id}", response_model=CollectionCenterRead)
def get_collection_center(
    db: DbSession,
    _: CurrentUser,
    center_id: int = Path(..., gt=0, description="Collection Center ID"),
):
    """
    Get a single collection center by ID.

    Any authenticated user can access this endpoint.
    """
    return collection_center_service.get_collection_center_or_404(db, center_id)


# ============================================================
# UPDATE COLLECTION CENTER
# ============================================================

@router.patch("/{center_id}", response_model=CollectionCenterRead)
def update_collection_center(
    payload: CollectionCenterUpdate,
    db: DbSession,
    _: CollectionCenterWriteUser,
    center_id: int = Path(..., gt=0, description="Collection Center ID"),
):
    """
    Partially update an existing collection center.

    Only ADMIN, LAB_MANAGER, and RECEPTIONIST can update collection centers.
    To change the active status use /status.
    """
    center = collection_center_service.get_collection_center_or_404(db, center_id)
    return collection_center_service.update_collection_center(db, center, payload)


# ============================================================
# UPDATE COLLECTION CENTER STATUS
# ============================================================

@router.patch("/{center_id}/status", response_model=CollectionCenterRead)
def update_collection_center_status(
    payload: StatusUpdate,
    db: DbSession,
    _: CollectionCenterManageUser,
    center_id: int = Path(..., gt=0, description="Collection Center ID"),
):
    """
    Activate or deactivate a collection center.

    Only ADMIN and LAB_MANAGER can change collection center status.
    """
    center = collection_center_service.get_collection_center_or_404(db, center_id)
    return collection_center_service.update_collection_center_status(db, center, payload.is_active)


# ============================================================
# GET PATIENTS FOR COLLECTION CENTER
# ============================================================

@router.get("/{center_id}/patients", response_model=list[PatientRead])
def list_collection_center_patients(
    db: DbSession,
    _: CurrentUser,
    center_id: int = Path(..., gt=0, description="Collection Center ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
):
    """
    Get all patients registered through a specific collection center.
    """
    collection_center_service.get_collection_center_or_404(db, center_id)
    return patient_service.list_patients(
        db,
        skip=skip,
        limit=limit,
        search=search,
        collection_center_id=center_id,
    )


# ============================================================
# GET COLLECTION CENTER STATS & COMMISSIONS
# ============================================================

@router.get("/{center_id}/stats", response_model=CollectionCenterStatsResponse)
def get_collection_center_stats(
    db: DbSession,
    _: CurrentUser,
    center_id: int = Path(..., gt=0, description="Collection Center ID"),
    from_date: date | None = Query(default=None, description="Start date for referral billing stats"),
    to_date: date | None = Query(default=None, description="End date for referral billing stats"),
):
    """
    Get business metrics, referral patient count, total sales, and earned commission.
    """
    return collection_center_service.get_collection_center_stats(
        db,
        center_id,
        from_date=from_date,
        to_date=to_date,
    )
