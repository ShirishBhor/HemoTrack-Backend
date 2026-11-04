"""
Author: Nikhil Yuvraj Mole
Date: 2026-11-02

Description:
API router for laboratory Package Master management.
Provides:
- Creating packages with associated test cases
- Listing and searching packages with filtering
- Getting package details with included tests
- Updating package metadata and test mappings
- Deactivating and reactivating packages
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.package import (
    PackageCreate,
    PackageRead,
    PackageUpdate,
    PackageWithTestsRead,
)
from app.services import package_service

router = APIRouter(
    prefix="/packages",
    tags=["packages"],
)

# Only Admin and Lab Manager can create, update, or deactivate packages
PackageWriteUser = Annotated[
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
    response_model=list[PackageRead],
    summary="List packages",
)
def list_packages(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(
        default=None,
        max_length=150,
        description="Search by package name or code",
    ),
    department_id: int | None = Query(
        default=None,
        description="Filter by department ID",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true for active packages, false for inactive packages)",
    ),
):
    """List laboratory packages with search, pagination, and department filter."""
    return package_service.list_packages(
        db,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
        search=search if isinstance(search, str) else None,
        department_id=department_id if isinstance(department_id, int) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )


@router.post(
    "",
    response_model=PackageWithTestsRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create package",
)
def create_package(
    payload: PackageCreate,
    db: DbSession,
    _: PackageWriteUser,
):
    """Create a new package with bundled test cases. ADMIN and LAB_MANAGER only."""
    return package_service.create_package(db, payload)


@router.get(
    "/search",
    response_model=list[PackageRead],
    summary="Search packages",
)
def search_packages(
    db: DbSession,
    _: CurrentUser,
    q: str = Query(..., min_length=1, max_length=150),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Quick search for packages by name or code."""
    return package_service.list_packages(
        db,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
        search=q,
        is_active=True,
    )


@router.get(
    "/{package_id}",
    response_model=PackageWithTestsRead,
    summary="Get package details",
)
def get_package(
    db: DbSession,
    _: CurrentUser,
    package_id: int = Path(..., gt=0),
):
    """Get package details along with all bundled test cases."""
    return package_service.get_package_or_404(
        db,
        package_id,
    )


@router.patch(
    "/{package_id}",
    response_model=PackageWithTestsRead,
    summary="Update package",
)
def update_package(
    payload: PackageUpdate,
    db: DbSession,
    _: PackageWriteUser,
    package_id: int = Path(..., gt=0),
):
    """Update package details or test case associations."""
    return package_service.update_package(
        db,
        package_id,
        payload,
    )


@router.patch(
    "/{package_id}/deactivate",
    response_model=PackageRead,
    summary="Deactivate package",
)
def deactivate_package(
    db: DbSession,
    _: PackageWriteUser,
    package_id: int = Path(..., gt=0),
):
    """Soft-delete / deactivate a package."""
    return package_service.deactivate_package(
        db,
        package_id,
    )


@router.patch(
    "/{package_id}/reactivate",
    response_model=PackageRead,
    summary="Reactivate package",
)
def reactivate_package(
    db: DbSession,
    _: PackageWriteUser,
    package_id: int = Path(..., gt=0),
):
    """Reactivate a previously deactivated package."""
    return package_service.reactivate_package(
        db,
        package_id,
    )
