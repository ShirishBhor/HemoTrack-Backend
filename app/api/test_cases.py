"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This API router provides CRUD operations for laboratory Test Cases.

Available operations:
- List and search Test Cases
- Create a Test Case
- Get a Test Case by ID
- Update a Test Case
- Deactivate a Test Case

The Test Case API stores master test definitions only.
Patient-specific test results and discounts will be implemented separately.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseRead,
    TestCaseUpdate,
)
from app.services import test_case_service


router = APIRouter(
    prefix="/test-cases",
    tags=["test-cases"],
)


# ============================================================
# TEST CASE WRITE PERMISSIONS
# ============================================================

TestCaseWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
        )
    ),
]


# ============================================================
# GET ALL TEST CASES
# ============================================================

@router.get(
    "",
    response_model=list[TestCaseRead],
)
def list_test_cases(
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
        min_length=1,
        max_length=255,
        description="Search by test name or test code",
    ),
    active_only: bool = Query(
        default=True,
        description="Return only active Test Cases",
    ),
):
    """
    Get all laboratory Test Cases.

    Supports:
    - Pagination
    - Search by test name/code
    - Active/inactive filtering
    """

    return test_case_service.list_test_cases(
        db,
        skip=skip,
        limit=limit,
        search=search,
        active_only=active_only,
    )


# ============================================================
# CREATE TEST CASE
# ============================================================

@router.post(
    "",
    response_model=TestCaseRead,
    status_code=status.HTTP_201_CREATED,
)
def create_test_case(
    payload: TestCaseCreate,
    db: DbSession,
    _: TestCaseWriteUser,
):
    """
    Create a new laboratory Test Case.

    Only ADMIN and LAB_MANAGER can create Test Cases.
    """

    return test_case_service.create_test_case(
        db,
        payload,
    )


# ============================================================
# GET TEST CASE BY ID
# ============================================================

@router.get(
    "/{test_case_id}",
    response_model=TestCaseRead,
)
def get_test_case(
    db: DbSession,
    _: CurrentUser,
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
):
    """
    Get one Test Case by ID.

    Any authenticated active user can access this endpoint.
    """

    return test_case_service.get_test_case_or_404(
        db,
        test_case_id,
    )


# ============================================================
# UPDATE TEST CASE
# ============================================================

@router.patch(
    "/{test_case_id}",
    response_model=TestCaseRead,
)
def update_test_case(
    payload: TestCaseUpdate,
    db: DbSession,
    _: TestCaseWriteUser,
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
):
    """
    Update an existing Test Case.

    Only ADMIN and LAB_MANAGER can update Test Cases.

    The test price can also be updated here.

    Example:
        Current price = 500
        Updated price = 550

    The updated price becomes the current master price
    for future patients.
    """

    test_case = test_case_service.get_test_case_or_404(
        db,
        test_case_id,
    )

    return test_case_service.update_test_case(
        db,
        test_case,
        payload,
    )


# ============================================================
# DEACTIVATE TEST CASE
# ============================================================

@router.delete(
    "/{test_case_id}",
    response_model=TestCaseRead,
)
def delete_test_case(
    db: DbSession,
    _: TestCaseWriteUser,
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
):
    """
    Deactivate a Test Case.

    Only ADMIN and LAB_MANAGER can deactivate Test Cases.

    The record is not permanently deleted.
    It is marked as inactive so existing references remain safe.
    """

    test_case = test_case_service.get_test_case_or_404(
        db,
        test_case_id,
    )

    return test_case_service.deactivate_test_case(
        db,
        test_case,
    )