
"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This router provides API endpoints for managing Test Parameters.
Test Parameters define the fields displayed in a laboratory test form.
Patient-specific result values are not stored through these endpoints.
"""


from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.test_parameter import (
    TestParameterCreate,
    TestParameterRead,
    TestParameterUpdate,
)
from app.services.test_parameter_service import (
    create_test_parameter,
    deactivate_test_parameter,
    get_test_parameter_or_404,
    list_test_parameters,
    update_test_parameter,
)


router = APIRouter(
    prefix="/test-parameters",
    tags=["test-parameters"],
)

TestParameterWriteUser = require_roles(
    UserRole.ADMIN,
    UserRole.LAB_MANAGER,
)


# ============================================================
# CREATE TEST PARAMETER
# ============================================================

@router.post(
    "",
    response_model=TestParameterRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(TestParameterWriteUser)],
)
def create_parameter(
    data: TestParameterCreate,
    db: DbSession,
):
    """
    Create a new Test Parameter for a Test Case.

    Only ADMIN and LAB_MANAGER can create Test Parameters.
    """
    return create_test_parameter(db=db, data=data)


# ============================================================
# GET ALL TEST PARAMETERS
# ============================================================

@router.get(
    "",
    response_model=list[TestParameterRead],
)
def get_parameters(
    db: DbSession,
    _: CurrentUser,
    test_case_id: int | None = Query(
        default=None,
        gt=0,
        description="Filter by Test Case ID",
    ),
    active_only: bool = Query(
        default=True,
        description="Return only active Test Parameters",
    ),
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
):
    """
    Get all Test Parameters.

    Supports:
    - Filter by test_case_id
    - Active/inactive filtering
    - Pagination
    """
    return list_test_parameters(
        db=db,
        test_case_id=test_case_id,
        active_only=active_only,
        skip=skip,
        limit=limit,
    )


# ============================================================
# GET TEST PARAMETER BY ID
# ============================================================

@router.get(
    "/{test_parameter_id}",
    response_model=TestParameterRead,
)
def get_parameter(
    db: DbSession,
    _: CurrentUser,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
):
    """
    Get one Test Parameter by ID.

    Any authenticated active user can access this endpoint.
    """
    return get_test_parameter_or_404(
        db=db,
        test_parameter_id=test_parameter_id,
    )


# ============================================================
# UPDATE TEST PARAMETER
# ============================================================

@router.patch(
    "/{test_parameter_id}",
    response_model=TestParameterRead,
    dependencies=[Depends(TestParameterWriteUser)],
)
def update_parameter(
    db: DbSession,
    data: TestParameterUpdate,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
):
    """
    Update an existing Test Parameter.

    Only ADMIN and LAB_MANAGER can update Test Parameters.
    """
    return update_test_parameter(
        db=db,
        test_parameter_id=test_parameter_id,
        data=data,
    )


# ============================================================
# DEACTIVATE TEST PARAMETER
# ============================================================

@router.patch(
    "/{test_parameter_id}/deactivate",
    response_model=TestParameterRead,
    dependencies=[Depends(TestParameterWriteUser)],
)
def deactivate_parameter(
    db: DbSession,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
):
    """
    Deactivate a Test Parameter.

    Only ADMIN and LAB_MANAGER can deactivate Test Parameters.

    The record is not permanently deleted.
    It is marked as inactive so existing references remain safe.
    """
    return deactivate_test_parameter(
        db=db,
        test_parameter_id=test_parameter_id,
    )