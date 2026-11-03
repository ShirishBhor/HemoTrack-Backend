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

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.test_case import (
    TestCaseCreate,
    TestCaseRead,
    TestCaseUpdate,
    TestCaseWithParametersRead,
)
from app.schemas.test_parameter import (
    CopyParametersRequest,
    CopyParametersResponse,
    ParameterOrderItem,
    ParameterReorderRequest,
    TestParameterBulkCreate,
    TestParameterBulkItem,
    TestParameterRead,
)
from app.services import test_case_service, test_parameter_service


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
    department_id: int | None = Query(
        default=None,
        gt=0,
        description="Filter by Department ID",
    ),
):
    """
    Get all laboratory Test Cases.

    Supports:
    - Pagination
    - Search by test name/code
    - Active/inactive filtering
    - Filter by department
    """

    return test_case_service.list_test_cases(
        db,
        skip=skip,
        limit=limit,
        search=search,
        active_only=active_only,
        department_id=department_id,
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
# GET TEST CASE WITH PARAMETERS
# ============================================================

@router.get(
    "/{test_case_id}/with-parameters",
    response_model=TestCaseWithParametersRead,
)
def get_test_case_with_parameters(
    db: DbSession,
    _: CurrentUser,
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
    active_only: bool = Query(
        default=True,
        description="Return only active test parameters",
    ),
):
    """
    Get one Test Case by ID together with its parameters.

    Uses the existing SQLAlchemy relationship (TestCase.parameters)
    ordered by display_order.
    """
    test_case = test_case_service.get_test_case_with_parameters_or_404(
        db,
        test_case_id,
    )
    params = [
        p for p in test_case.parameters
        if (not active_only or p.is_active)
    ]
    params.sort(key=lambda p: (p.display_order, p.id))

    result = TestCaseWithParametersRead.model_validate(test_case)
    result.parameters = [TestParameterRead.model_validate(p) for p in params]
    return result


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

@router.patch(
    "/{test_case_id}/deactivate",
    response_model=TestCaseRead,
)
def deactivate_test_case(
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


# ============================================================
# REACTIVATE TEST CASE
# ============================================================

@router.patch(
    "/{test_case_id}/reactivate",
    response_model=TestCaseRead,
)
def reactivate_test_case(
    db: DbSession,
    _: TestCaseWriteUser,
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
):
    """
    Reactivate a previously deactivated Test Case.

    Only ADMIN and LAB_MANAGER can reactivate Test Cases.
    """
    test_case = test_case_service.get_test_case_or_404(
        db,
        test_case_id,
    )

    return test_case_service.reactivate_test_case(
        db,
        test_case,
    )


# ============================================================
# BULK CREATE TEST PARAMETERS FOR TEST CASE
# ============================================================

@router.post(
    "/{test_case_id}/parameters/bulk",
    response_model=list[TestParameterRead],
    status_code=status.HTTP_201_CREATED,
)
def bulk_create_parameters(
    db: DbSession,
    _: TestCaseWriteUser,
    payload: list[TestParameterBulkItem] | TestParameterBulkCreate = Body(
        ...,
        description="List of parameters to add in bulk, either as a JSON array or wrapped object",
    ),
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
):
    """
    Add multiple Test Parameters in bulk to a Test Case.

    Only ADMIN and LAB_MANAGER can bulk create parameters.
    """
    items = payload if isinstance(payload, list) else payload.parameters
    return test_parameter_service.bulk_create_test_parameters(
        db=db,
        test_case_id=test_case_id,
        items=items,
    )


# ============================================================
# REORDER TEST PARAMETERS FOR TEST CASE
# ============================================================

@router.patch(
    "/{test_case_id}/parameters/reorder",
    response_model=list[TestParameterRead],
)
def reorder_parameters(
    db: DbSession,
    _: TestCaseWriteUser,
    payload: list[ParameterOrderItem] | ParameterReorderRequest | list[int] = Body(
        ...,
        description="Sequential display order updates, as ordered IDs or ID-to-order mappings",
    ),
    test_case_id: int = Path(
        ...,
        gt=0,
        description="Test Case ID",
    ),
):
    """
    Update display orders of parameters for a Test Case sequentially.

    Accepts:
    - Array of items: `[{"id": 1, "display_order": 1}, {"id": 2, "display_order": 2}]`
    - Object with orders: `{"orders": [{"id": 1, "display_order": 1}]}`
    - Array of IDs in sequence: `[10, 15, 12]`
    - Object with parameter_ids: `{"parameter_ids": [10, 15, 12]}`

    Only ADMIN and LAB_MANAGER can reorder Test Parameters.
    """
    updates: dict[int, int] = {}
    if isinstance(payload, list):
        if payload and isinstance(payload[0], int):
            updates = {pid: idx + 1 for idx, pid in enumerate(payload)}
        else:
            updates = {item.id: item.display_order for item in payload}
    elif isinstance(payload, ParameterReorderRequest):
        if payload.parameter_ids is not None:
            updates = {pid: idx + 1 for idx, pid in enumerate(payload.parameter_ids)}
        else:
            updates = {item.id: item.display_order for item in payload.orders}

    return test_parameter_service.reorder_test_parameters(
        db=db,
        test_case_id=test_case_id,
        updates=updates,
    )


# ============================================================
# COPY TEST PARAMETERS FROM ANOTHER TEST CASE
# ============================================================

@router.post(
    "/{target_test_case_id}/parameters/copy-from/{source_test_case_id}",
    response_model=CopyParametersResponse,
    status_code=status.HTTP_201_CREATED,
)
def copy_parameters(
    db: DbSession,
    _: TestCaseWriteUser,
    target_test_case_id: int = Path(
        ...,
        gt=0,
        description="Target Test Case ID to copy parameters into",
    ),
    source_test_case_id: int = Path(
        ...,
        gt=0,
        description="Source Test Case ID to copy parameters from",
    ),
    payload: CopyParametersRequest = Body(
        default=CopyParametersRequest(),
        description="Copy options (overwrite_existing: true/false)",
    ),
):
    """
    Copy active parameters from a source Test Case into the target Test Case.

    Supports `overwrite_existing=false` (default: skip existing codes)
    or `overwrite_existing=true` (overwrite parameters with matching codes).

    Only ADMIN and LAB_MANAGER can copy parameters.
    """
    return test_parameter_service.copy_parameters_between_tests(
        db=db,
        source_test_case_id=source_test_case_id,
        target_test_case_id=target_test_case_id,
        overwrite_existing=payload.overwrite_existing,
    )