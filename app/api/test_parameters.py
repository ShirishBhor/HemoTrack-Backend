
"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This router provides API endpoints for managing Test Parameters.
Test Parameters define the fields displayed in a laboratory test form.
Patient-specific result values are not stored through these endpoints.
"""


from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import UserRole
from app.schemas.test_parameter import (
    FormulaValidationRequest,
    FormulaValidationResponse,
    ParameterReferenceRangeCreate,
    ParameterReferenceRangeRead,
    ParameterReferenceRangeUpdate,
    TestParameterCreate,
    TestParameterRead,
    TestParameterUpdate,
)
from app.services.test_parameter_service import (
    create_reference_range,
    create_test_parameter,
    deactivate_test_parameter,
    delete_reference_range,
    delete_test_parameter,
    get_distinct_units,
    get_test_parameter_or_404,
    list_reference_ranges,
    list_test_parameters,
    reactivate_test_parameter,
    update_reference_range,
    update_test_parameter,
    validate_formula_for_test_case,
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
    test_case_id: Annotated[
        int | None,
        Query(
            gt=0,
            description="Filter by Test Case ID",
        ),
    ] = None,
    search: Annotated[
        str | None,
        Query(
            max_length=255,
            description="Search by parameter name or parameter code",
        ),
    ] = None,
    is_active: Annotated[
        bool | None,
        Query(
            description="Filter by active status (true for active test parameters, false for inactive test parameters)",
        ),
    ] = None,
    skip: Annotated[
        int,
        Query(
            ge=0,
            description="Number of records to skip",
        ),
    ] = 0,
    limit: Annotated[
        int,
        Query(
            ge=1,
            le=200,
            description="Maximum number of records to return",
        ),
    ] = 50,
):
    """
    Get all Test Parameters.

    Supports:
    - Filter by test_case_id
    - Search by parameter name/code
    - Active/inactive filtering
    - Pagination
    """
    return list_test_parameters(
        db=db,
        test_case_id=test_case_id,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
    )


# ============================================================
# GET STANDARD AND USED MEASUREMENT UNITS
# ============================================================

@router.get(
    "/units",
    response_model=list[str],
)
def list_units(
    db: DbSession,
    _: CurrentUser,
):
    """
    Get distinct laboratory measurement units used across the system,
    merged with standard clinical units catalog.
    """
    return get_distinct_units(db=db)


# ============================================================
# VALIDATE FORMULA FOR TEST CASE
# ============================================================

@router.post(
    "/validate-formula",
    response_model=FormulaValidationResponse,
    dependencies=[Depends(TestParameterWriteUser)],
)
def validate_formula(
    payload: FormulaValidationRequest,
    db: DbSession,
):
    """
    Validate a mathematical formula against parameter codes in a test case.

    Only ADMIN and LAB_MANAGER can validate test formulas.
    """
    return validate_formula_for_test_case(
        db=db,
        test_case_id=payload.test_case_id,
        formula=payload.formula,
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


# ============================================================
# REACTIVATE TEST PARAMETER
# ============================================================

@router.patch(
    "/{test_parameter_id}/reactivate",
    response_model=TestParameterRead,
    dependencies=[Depends(TestParameterWriteUser)],
)
def reactivate_parameter(
    db: DbSession,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
):
    """
    Reactivate a previously deactivated Test Parameter.

    Only ADMIN and LAB_MANAGER can reactivate Test Parameters.
    """
    return reactivate_test_parameter(
        db=db,
        test_parameter_id=test_parameter_id,
    )


# ============================================================
# DELETE TEST PARAMETER
# ============================================================

@router.delete(
    "/{test_parameter_id}",
    dependencies=[Depends(TestParameterWriteUser)],
)
def delete_parameter(
    db: DbSession,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
):
    """
    Permanently delete a Test Parameter.

    Only ADMIN and LAB_MANAGER can delete Test Parameters.
    """
    return delete_test_parameter(
        db=db,
        test_parameter_id=test_parameter_id,
    )


# ============================================================
# REFERENCE RANGES (AGE AND GENDER SPECIFIC)
# ============================================================

@router.get(
    "/{test_parameter_id}/reference-ranges",
    response_model=list[ParameterReferenceRangeRead],
)
def get_parameter_reference_ranges(
    db: DbSession,
    _: CurrentUser,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true for active reference ranges, false for inactive reference ranges)",
    ),
):
    """
    Get all age- and gender-specific reference ranges for a Test Parameter.
    """
    return list_reference_ranges(
        db=db,
        parameter_id=test_parameter_id,
        is_active=is_active if isinstance(is_active, bool) else None,
    )


@router.post(
    "/{test_parameter_id}/reference-ranges",
    response_model=ParameterReferenceRangeRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(TestParameterWriteUser)],
)
def add_parameter_reference_range(
    db: DbSession,
    payload: ParameterReferenceRangeCreate,
    test_parameter_id: int = Path(
        ...,
        gt=0,
        description="Test Parameter ID",
    ),
):
    """
    Add a new age- and gender-specific reference range to a Test Parameter.

    Only ADMIN and LAB_MANAGER can create reference ranges.
    """
    return create_reference_range(
        db=db,
        parameter_id=test_parameter_id,
        payload=payload,
    )


@router.patch(
    "/reference-ranges/{range_id}",
    response_model=ParameterReferenceRangeRead,
    dependencies=[Depends(TestParameterWriteUser)],
)
def update_range(
    db: DbSession,
    payload: ParameterReferenceRangeUpdate,
    range_id: int = Path(
        ...,
        gt=0,
        description="Reference Range ID",
    ),
):
    """
    Update an existing reference range.

    Only ADMIN and LAB_MANAGER can update reference ranges.
    """
    return update_reference_range(
        db=db,
        range_id=range_id,
        payload=payload,
    )


@router.delete(
    "/reference-ranges/{range_id}",
    dependencies=[Depends(TestParameterWriteUser)],
)
def delete_range(
    db: DbSession,
    range_id: int = Path(
        ...,
        gt=0,
        description="Reference Range ID",
    ),
):
    """
    Delete a reference range.

    Only ADMIN and LAB_MANAGER can delete reference ranges.
    """
    return delete_reference_range(
        db=db,
        range_id=range_id,
    )