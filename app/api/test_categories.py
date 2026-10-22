
"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-22

Description:
Provides CRUD, search, deactivate, and reactivate
operations for laboratory Test Categories.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.test_category import (
    TestCategoryCreate,
    TestCategoryRead,
    TestCategoryUpdate,
)
from app.services import test_category_service


router = APIRouter(
    prefix="/test-categories",
    tags=["test-categories"],
)


TestCategoryWriteUser = Annotated[
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
    response_model=list[TestCategoryRead],
)
def list_test_categories(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
    ),
    active_only: bool = True,
):
    """List categories with search and pagination."""
    return test_category_service.list_categories(
        db,
        skip=skip,
        limit=limit,
        search=search,
        active_only=active_only,
    )


@router.post(
    "",
    response_model=TestCategoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_category(
    payload: TestCategoryCreate,
    db: DbSession,
    _: TestCategoryWriteUser,
):
    """Create a category. ADMIN and LAB_MANAGER only."""
    return test_category_service.create_category(db, payload)


# Keep this route before /{category_id}.
@router.get(
    "/search",
    response_model=list[TestCategoryRead],
)
def search_test_categories(
    db: DbSession,
    _: CurrentUser,
    q: str = Query(..., min_length=1, max_length=150),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
):
    """Search categories by name or code."""
    return test_category_service.list_categories(
        db,
        skip=skip,
        limit=limit,
        search=q,
        active_only=True,
    )


@router.get(
    "/{category_id}",
    response_model=TestCategoryRead,
)
def get_test_category(
    db: DbSession,
    _: CurrentUser,
    category_id: int = Path(..., gt=0),
):
    """Get a category by ID."""
    return test_category_service.get_category_or_404(
        db,
        category_id,
    )


@router.patch(
    "/{category_id}",
    response_model=TestCategoryRead,
)
def update_test_category(
    payload: TestCategoryUpdate,
    db: DbSession,
    _: TestCategoryWriteUser,
    category_id: int = Path(..., gt=0),
):
    """Update supplied category fields."""
    return test_category_service.update_category(
        db,
        category_id,
        payload,
    )


@router.patch(
    "/{category_id}/deactivate",
    response_model=TestCategoryRead,
)
def deactivate_test_category(
    db: DbSession,
    _: TestCategoryWriteUser,
    category_id: int = Path(..., gt=0),
):
    """Soft-delete a category."""
    return test_category_service.deactivate_category(
        db,
        category_id,
    )


@router.patch(
    "/{category_id}/reactivate",
    response_model=TestCategoryRead,
)
def reactivate_test_category(
    db: DbSession,
    _: TestCategoryWriteUser,
    category_id: int = Path(..., gt=0),
):
    """Reactivate an inactive category."""
    return test_category_service.reactivate_category(
        db,
        category_id,
    )
