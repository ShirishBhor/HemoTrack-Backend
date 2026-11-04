"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This service module contains business logic for Test Parameters.
It handles creating, retrieving, updating, and deactivating
test parameters while keeping database operations outside
the API route layer.
"""

import json
import logging
import re

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.parameter_reference_range import ParameterReferenceRange
from app.models.test_case import TestCase
from app.models.test_parameter import TestParameter
from app.schemas.test_parameter import (
    ParameterReferenceRangeCreate,
    ParameterReferenceRangeUpdate,
    TestParameterBulkItem,
    TestParameterCreate,
    TestParameterUpdate,
)

logger = logging.getLogger(__name__)


def _format_options(val: list[str] | str | None) -> str | None:
    if val is None:
        return None
    if isinstance(val, list):
        clean = [str(x).strip() for x in val if str(x).strip()]
        return json.dumps(clean) if clean else None
    val = val.strip()
    return val if val else None


def get_test_parameter_or_404(
    db: Session,
    test_parameter_id: int,
) -> TestParameter:
    """
    Get a Test Parameter by ID.

    Raises:
        HTTPException: If Test Parameter does not exist.
    """
    parameter = db.get(TestParameter, test_parameter_id)

    if parameter is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test parameter not found.",
        )

    return parameter


def create_test_parameter(
    db: Session,
    data: TestParameterCreate,
) -> TestParameter:
    """
    Create a new Test Parameter for a Test Case.
    """
    test_case = db.get(TestCase, data.test_case_id)

    if test_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    if not test_case.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add parameters to an inactive test case.",
        )

    code = data.code.strip().upper()

    existing = db.scalar(
        select(TestParameter).where(
            TestParameter.test_case_id == data.test_case_id,
            TestParameter.code == code,
        )
    )

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This parameter code already exists for this test case.",
        )

    dumped = data.model_dump()
    if "options" in dumped:
        dumped["options"] = _format_options(dumped["options"])
    dumped["code"] = code

    parameter = TestParameter(**dumped)

    try:
        db.add(parameter)
        db.commit()
        db.refresh(parameter)
        return parameter
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate parameter code or invalid database reference.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to create test parameter", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test parameter.",
        ) from exc


def list_test_parameters(
    db: Session,
    test_case_id: int | None = None,
    search: str | None = None,
    skip: int = 0,
    limit: int = 50,
    is_active: bool | None = None,
) -> list[TestParameter]:
    """
    Return Test Parameters with optional filtering, search, and pagination.
    """
    query = select(TestParameter)

    if test_case_id is not None:
        query = query.where(
            TestParameter.test_case_id == test_case_id
        )

    if isinstance(is_active, bool):
        query = query.where(TestParameter.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                TestParameter.name.ilike(pattern),
                TestParameter.code.ilike(pattern),
            )
        )

    safe_skip = skip if isinstance(skip, int) else 0
    safe_limit = limit if isinstance(limit, int) else 50
    query = (
        query.order_by(
            TestParameter.test_case_id,
            TestParameter.display_order,
            TestParameter.id,
        )
        .offset(safe_skip)
        .limit(safe_limit)
    )

    return list(db.scalars(query).all())


def update_test_parameter(
    db: Session,
    test_parameter_id: int,
    data: TestParameterUpdate,
) -> TestParameter:
    """
    Update only the fields supplied by the client.
    """
    parameter = get_test_parameter_or_404(
        db,
        test_parameter_id,
    )

    changes = data.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required for update.",
        )

    if "code" in changes and changes["code"] is not None:
        changes["code"] = changes["code"].strip().upper()

        existing = db.scalar(
            select(TestParameter).where(
                TestParameter.test_case_id == parameter.test_case_id,
                TestParameter.code == changes["code"],
                TestParameter.id != parameter.id,
            )
        )

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This parameter code already exists for this test case.",
            )

    if "options" in changes:
        changes["options"] = _format_options(changes["options"])

    for field, value in changes.items():
        setattr(parameter, field, value)

    try:
        db.commit()
        db.refresh(parameter)
        return parameter
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="The update violates a database constraint.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to update test parameter", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update test parameter.",
        ) from exc


def deactivate_test_parameter(
    db: Session,
    test_parameter_id: int,
) -> TestParameter:
    """
    Deactivate a Test Parameter instead of permanently deleting it.

    This is a soft delete.
    """
    parameter = get_test_parameter_or_404(
        db,
        test_parameter_id,
    )

    if not parameter.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test parameter is already inactive.",
        )

    parameter.is_active = False

    try:
        db.commit()
        db.refresh(parameter)
        return parameter
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to deactivate test parameter", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate test parameter.",
        ) from exc


def reactivate_test_parameter(
    db: Session,
    test_parameter_id: int,
) -> TestParameter:
    """
    Reactivate a previously deactivated Test Parameter.
    """
    parameter = get_test_parameter_or_404(
        db,
        test_parameter_id,
    )

    if parameter.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test parameter is already active.",
        )

    test_case = db.get(TestCase, parameter.test_case_id)
    if test_case and not test_case.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reactivate parameter for an inactive test case.",
        )

    parameter.is_active = True

    try:
        db.commit()
        db.refresh(parameter)
        return parameter
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to reactivate test parameter", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate test parameter.",
        ) from exc


def bulk_create_test_parameters(
    db: Session,
    test_case_id: int,
    items: list[TestParameterBulkItem],
) -> list[TestParameter]:
    """
    Create multiple Test Parameters in bulk for a given Test Case.
    """
    test_case = db.get(TestCase, test_case_id)
    if test_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    if not test_case.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add parameters to an inactive test case.",
        )

    if not items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Parameter list cannot be empty.",
        )

    # Check for duplicate codes within the incoming payload
    payload_codes = [item.code.strip().upper() for item in items]
    if len(payload_codes) != len(set(payload_codes)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate parameter codes found in the request payload.",
        )

    # Check for duplicates against existing parameters for this test case
    existing_codes = set(
        db.scalars(
            select(TestParameter.code).where(
                TestParameter.test_case_id == test_case_id
            )
        ).all()
    )
    conflicts = [code for code in payload_codes if code in existing_codes]
    if conflicts:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Parameter codes already exist for this test case: {', '.join(conflicts)}",
        )

    # Determine current max display_order for auto-incrementing if not provided
    max_order = (
        db.scalar(
            select(func.max(TestParameter.display_order)).where(
                TestParameter.test_case_id == test_case_id
            )
        )
        or 0
    )

    new_params: list[TestParameter] = []
    current_order = max_order
    for item in items:
        current_order += 1
        order = item.display_order if item.display_order is not None else current_order
        options_val = _format_options(item.options)
        param = TestParameter(
            test_case_id=test_case_id,
            name=item.name.strip(),
            code=item.code.strip().upper(),
            unit=item.unit.strip() if item.unit else None,
            normal_range=item.normal_range.strip() if item.normal_range else None,
            description=item.description.strip() if item.description else None,
            data_type=item.data_type.strip().lower(),
            options=options_val,
            is_calculated=item.is_calculated,
            formula=item.formula.strip() if item.formula else None,
            critical_low=item.critical_low.strip() if item.critical_low else None,
            critical_high=item.critical_high.strip() if item.critical_high else None,
            critical_action=item.critical_action.strip() if item.critical_action else None,
            is_required=item.is_required,
            display_order=order,
            is_active=True,
        )
        new_params.append(param)

    try:
        db.add_all(new_params)
        db.commit()
        for p in new_params:
            db.refresh(p)
        return new_params
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Duplicate parameter code or invalid database reference.",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to bulk create test parameters", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to bulk create test parameters.",
        ) from exc


def reorder_test_parameters(
    db: Session,
    test_case_id: int,
    updates: dict[int, int],
) -> list[TestParameter]:
    """
    Update display orders of test parameters for a given Test Case.
    """
    test_case = db.get(TestCase, test_case_id)
    if test_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reorder updates cannot be empty.",
        )

    existing_params = {
        p.id: p
        for p in db.scalars(
            select(TestParameter).where(
                TestParameter.test_case_id == test_case_id
            )
        ).all()
    }

    invalid_ids = [pid for pid in updates.keys() if pid not in existing_params]
    if invalid_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Parameters do not belong to this test case: {invalid_ids}",
        )

    for pid, new_order in updates.items():
        existing_params[pid].display_order = new_order
        db.add(existing_params[pid])

    try:
        db.commit()
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to reorder test parameters", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update parameter display orders.",
        ) from exc

    return list(
        db.scalars(
            select(TestParameter)
            .where(TestParameter.test_case_id == test_case_id)
            .order_by(TestParameter.display_order.asc(), TestParameter.id.asc())
        ).all()
    )


def delete_test_parameter(
    db: Session,
    test_parameter_id: int,
) -> dict:
    """
    Permanently delete a Test Parameter.
    """
    parameter = get_test_parameter_or_404(
        db,
        test_parameter_id,
    )

    db.delete(parameter)
    try:
        db.commit()
        return {
            "message": "Test parameter deleted successfully",
            "id": test_parameter_id,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to delete test parameter", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete test parameter.",
        ) from exc


# Predefined standard laboratory measurement units
STANDARD_PATHOLOGY_UNITS = [
    "%",
    "/HPF",
    "/LPF",
    "AU/mL",
    "cells/mcL",
    "copies/mL",
    "fl",
    "g/dL",
    "g/L",
    "index",
    "IU/L",
    "IU/mL",
    "mcg/dL",
    "mcg/mL",
    "mEq/L",
    "mg/dL",
    "mg/L",
    "mil/mcL",
    "min",
    "mIU/L",
    "mIU/mL",
    "mm/hr",
    "mmol/L",
    "ng/dL",
    "ng/mL",
    "pg",
    "pg/mL",
    "ratio",
    "sec",
    "thou/mcL",
    "titer",
    "U/L",
    "µmol/L",
]


def get_distinct_units(db: Session) -> list[str]:
    """
    Return distinct parameter units found in the database merged with
    standard clinical pathology units.
    """
    db_units = db.scalars(
        select(TestParameter.unit)
        .where(TestParameter.unit.isnot(None))
        .distinct()
    ).all()

    combined = set(STANDARD_PATHOLOGY_UNITS)
    for u in db_units:
        if u and u.strip():
            combined.add(u.strip())

    return sorted(list(combined), key=lambda x: x.lower())


def copy_parameters_between_tests(
    db: Session,
    source_test_case_id: int,
    target_test_case_id: int,
    overwrite_existing: bool = False,
) -> dict:
    """
    Copy active parameters from a source Test Case to a target Test Case.
    """
    source_tc = db.get(TestCase, source_test_case_id)
    if not source_tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source test case not found.",
        )

    target_tc = db.get(TestCase, target_test_case_id)
    if not target_tc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target test case not found.",
        )

    if not target_tc.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot copy parameters into an inactive test case.",
        )

    if source_test_case_id == target_test_case_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Source and target test cases must be different.",
        )

    source_params = db.scalars(
        select(TestParameter)
        .where(TestParameter.test_case_id == source_test_case_id)
        .where(TestParameter.is_active.is_(True))
        .order_by(TestParameter.display_order.asc(), TestParameter.id.asc())
    ).all()

    if not source_params:
        return {
            "copied_count": 0,
            "skipped_count": 0,
            "parameters": [],
        }

    target_existing = {
        p.code: p
        for p in db.scalars(
            select(TestParameter).where(
                TestParameter.test_case_id == target_test_case_id
            )
        ).all()
    }

    max_order = (
        db.scalar(
            select(func.max(TestParameter.display_order)).where(
                TestParameter.test_case_id == target_test_case_id
            )
        )
        or 0
    )

    copied: list[TestParameter] = []
    skipped = 0

    for sp in source_params:
        if sp.code in target_existing:
            if not overwrite_existing:
                skipped += 1
                continue
            else:
                tp = target_existing[sp.code]
                tp.name = sp.name
                tp.unit = sp.unit
                tp.normal_range = sp.normal_range
                tp.description = sp.description
                tp.data_type = sp.data_type
                tp.options = sp.options
                tp.is_calculated = sp.is_calculated
                tp.formula = sp.formula
                tp.critical_low = sp.critical_low
                tp.critical_high = sp.critical_high
                tp.critical_action = sp.critical_action
                tp.is_required = sp.is_required
                tp.is_active = True
                db.add(tp)
                copied.append(tp)
                continue

        max_order += 1
        new_p = TestParameter(
            test_case_id=target_test_case_id,
            name=sp.name,
            code=sp.code,
            unit=sp.unit,
            normal_range=sp.normal_range,
            description=sp.description,
            data_type=sp.data_type,
            options=sp.options,
            is_calculated=sp.is_calculated,
            formula=sp.formula,
            critical_low=sp.critical_low,
            critical_high=sp.critical_high,
            critical_action=sp.critical_action,
            is_required=sp.is_required,
            display_order=max_order,
            is_active=True,
        )
        db.add(new_p)
        copied.append(new_p)

    try:
        db.commit()
        for p in copied:
            db.refresh(p)
        return {
            "copied_count": len(copied),
            "skipped_count": skipped,
            "parameters": copied,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to copy parameters between test cases", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to copy parameters.",
        ) from exc


def validate_formula_for_test_case(
    db: Session,
    test_case_id: int,
    formula: str,
) -> dict:
    """
    Validate that all referenced parameter codes in a formula exist in the specified test case.
    """
    test_case = db.get(TestCase, test_case_id)
    if not test_case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found.",
        )

    # Extract variable codes matching {CODE}
    variables = re.findall(r"\{([A-Za-z0-9_-]+)\}", formula)
    if not variables:
        return {
            "is_valid": False,
            "variables": [],
            "missing_variables": [],
            "message": "No parameter variables found. Enclose parameter codes in curly brackets, e.g. {TP} - {ALB}",
        }

    unique_vars = sorted(list(set(v.upper() for v in variables)))
    existing_codes = set(
        db.scalars(
            select(TestParameter.code).where(
                TestParameter.test_case_id == test_case_id,
                TestParameter.is_active.is_(True),
            )
        ).all()
    )

    missing = [v for v in unique_vars if v not in existing_codes]
    if missing:
        return {
            "is_valid": False,
            "variables": unique_vars,
            "missing_variables": missing,
            "message": f"Formula references missing parameter codes: {', '.join(missing)}",
        }

    return {
        "is_valid": True,
        "variables": unique_vars,
        "missing_variables": [],
        "message": "Formula syntax and parameter codes are valid.",
    }


# ============================================================
# REFERENCE RANGE SERVICES
# ============================================================

def list_reference_ranges(
    db: Session,
    parameter_id: int,
    is_active: bool | None = None,
) -> list[ParameterReferenceRange]:
    """
    List age/gender reference ranges for a parameter.
    """
    get_test_parameter_or_404(db, parameter_id)

    query = select(ParameterReferenceRange).where(
        ParameterReferenceRange.parameter_id == parameter_id
    )

    if isinstance(is_active, bool):
        query = query.where(ParameterReferenceRange.is_active.is_(is_active))

    query = query.order_by(
        ParameterReferenceRange.min_age_days.asc(),
        ParameterReferenceRange.gender.asc(),
        ParameterReferenceRange.id.asc(),
    )

    return list(db.scalars(query).all())


def create_reference_range(
    db: Session,
    parameter_id: int,
    payload: ParameterReferenceRangeCreate,
) -> ParameterReferenceRange:
    """
    Create a new age/gender reference range for a parameter.
    """
    parameter = get_test_parameter_or_404(db, parameter_id)
    if not parameter.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot add reference ranges to an inactive parameter.",
        )

    rr = ParameterReferenceRange(
        parameter_id=parameter_id,
        **payload.model_dump(),
    )

    try:
        db.add(rr)
        db.commit()
        db.refresh(rr)
        return rr
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to create reference range", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create reference range.",
        ) from exc


def update_reference_range(
    db: Session,
    range_id: int,
    payload: ParameterReferenceRangeUpdate,
) -> ParameterReferenceRange:
    """
    Update an existing reference range.
    """
    rr = db.get(ParameterReferenceRange, range_id)
    if not rr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference range not found.",
        )

    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(rr, field, value)

    try:
        db.commit()
        db.refresh(rr)
        return rr
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to update reference range", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update reference range.",
        ) from exc


def delete_reference_range(
    db: Session,
    range_id: int,
) -> dict:
    """
    Delete a reference range.
    """
    rr = db.get(ParameterReferenceRange, range_id)
    if not rr:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reference range not found.",
        )

    db.delete(rr)
    try:
        db.commit()
        return {
            "message": "Reference range deleted successfully",
            "id": range_id,
        }
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Failed to delete reference range", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete reference range.",
        ) from exc