"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This service module contains business logic for Test Parameters.
It handles creating, retrieving, updating, and deactivating
test parameters while keeping database operations outside
the API route layer.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.test_case import TestCase
from app.models.test_parameter import TestParameter
from app.schemas.test_parameter import (
    TestParameterCreate,
    TestParameterUpdate,
)

logger = logging.getLogger(__name__)


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

    parameter = TestParameter(
        **{
            **data.model_dump(),
            "code": code,
        }
    )

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
    active_only: bool = True,
    skip: int = 0,
    limit: int = 50,
) -> list[TestParameter]:
    """
    Return Test Parameters with optional filtering and pagination.
    """
    query = select(TestParameter)

    if test_case_id is not None:
        query = query.where(
            TestParameter.test_case_id == test_case_id
        )

    if active_only:
        query = query.where(TestParameter.is_active.is_(True))

    query = (
        query.order_by(
            TestParameter.test_case_id,
            TestParameter.display_order,
            TestParameter.id,
        )
        .offset(skip)
        .limit(limit)
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