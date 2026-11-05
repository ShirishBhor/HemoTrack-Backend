"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-22

Description:
Provides CRUD, search, and status update (activate/deactivate)
operations for laboratory Departments.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.common import StatusUpdate
from app.schemas.department import (
    DepartmentCreate,
    DepartmentRead,
    DepartmentUpdate,
)
from app.services import department_service


router = APIRouter(
    prefix="/departments",
    tags=["departments"],
)


DepartmentWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
        )
    ),
]


@router.get(
    "",
    response_model=list[DepartmentRead],
)
def list_departments(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(
        default=None,
        max_length=150,
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true for active departments, false for inactive departments)",
    ),
):
    """List departments with search and pagination."""
    return department_service.list_departments(
        db,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )


@router.post(
    "",
    response_model=DepartmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_department(
    payload: DepartmentCreate,
    db: DbSession,
    _: DepartmentWriteUser,
):
    """Create a department. ADMIN and LAB_MANAGER only."""
    return department_service.create_department(db, payload)


# Keep this route before /{department_id}.
@router.get(
    "/search",
    response_model=list[DepartmentRead],
)
def search_departments(
    db: DbSession,
    _: CurrentUser,
    q: str = Query(..., min_length=1, max_length=150),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Search departments by name or code."""
    return department_service.list_departments(
        db,
        skip=skip,
        limit=limit,
        search=q,
        is_active=True,
    )


@router.get(
    "/{department_id}",
    response_model=DepartmentRead,
)
def get_department(
    db: DbSession,
    _: CurrentUser,
    department_id: int = Path(..., gt=0),
):
    """Get a department by ID."""
    return department_service.get_department_or_404(
        db,
        department_id,
    )


@router.patch(
    "/{department_id}",
    response_model=DepartmentRead,
)
def update_department(
    payload: DepartmentUpdate,
    db: DbSession,
    _: DepartmentWriteUser,
    department_id: int = Path(..., gt=0),
):
    """Update supplied department fields."""
    return department_service.update_department(
        db,
        department_id,
        payload,
    )


@router.patch(
    "/{department_id}/status",
    response_model=DepartmentRead,
)
def update_department_status(
    department_id: int,
    payload: StatusUpdate,
    db: DbSession,
    _: DepartmentWriteUser,
):
    """Activate or deactivate a department."""
    return department_service.update_department_status(
        db,
        department_id=department_id,
        is_active=payload.is_active,
    )
