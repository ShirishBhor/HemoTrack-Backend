"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-05

Description:
This service file contains the business logic for Test Case management.

It handles:
- Creating Test Cases
- Reading Test Cases
- Searching Test Cases
- Updating Test Cases
- Deactivating Test Cases

Patient-specific test results and discounts are not handled here.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, selectinload

from app.models.test_case import TestCase
from app.schemas.test_case import TestCaseCreate, TestCaseUpdate

logger = logging.getLogger(__name__)


def get_test_case(
    db: Session,
    test_case_id: int,
) -> TestCase | None:
    """
    Get a Test Case by its ID.
    """

    return db.get(TestCase, test_case_id)


def get_test_case_or_404(
    db: Session,
    test_case_id: int,
) -> TestCase:
    """
    Get a Test Case by ID.

    Raises:
        HTTPException: If Test Case does not exist.
    """

    test_case = get_test_case(
        db=db,
        test_case_id=test_case_id,
    )

    if test_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )

    return test_case


def list_test_cases(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    active_only: bool = True,
) -> list[TestCase]:
    """
    Return Test Cases with:

    - Pagination
    - Search by name/code
    - Active/inactive filtering
    """

    query = select(TestCase)

    # Return only active tests by default
    if active_only:
        query = query.where(
            TestCase.is_active.is_(True)
        )

    # Search by test name or test code
    if search:
        search = search.strip()

        if search:
            search_pattern = f"%{search}%"

            query = query.where(
                or_(
                    TestCase.name.ilike(search_pattern),
                    TestCase.code.ilike(search_pattern),
                )
            )

    query = (
        query
        .order_by(TestCase.name.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(
        db.scalars(query).all()
    )


def create_test_case(
    db: Session,
    payload: TestCaseCreate,
) -> TestCase:
    """
    Create a new Test Case.
    """

    test_case = TestCase(
        **payload.model_dump()
    )

    try:
        db.add(test_case)

        db.commit()

        db.refresh(test_case)

    except IntegrityError as exc:
        db.rollback()

        logger.error("Test case integrity error on create", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Test case code already exists",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        logger.error("Test case database error on create", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test case",
        ) from exc

    return test_case


def update_test_case(
    db: Session,
    test_case: TestCase,
    payload: TestCaseUpdate,
) -> TestCase:
    """
    Update only the fields supplied by the client.
    """

    data = payload.model_dump(
        exclude_unset=True
    )

    if not data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required for update",
        )

    # Update supplied fields
    for field, value in data.items():
        setattr(
            test_case,
            field,
            value,
        )

    try:
        db.add(test_case)

        db.commit()

        db.refresh(test_case)

    except IntegrityError as exc:
        db.rollback()

        logger.error("Test case integrity error on update", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Test case code already exists",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()

        logger.error("Test case database error on update", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update test case",
        ) from exc

    return test_case


def deactivate_test_case(
    db: Session,
    test_case: TestCase,
) -> TestCase:
    """
    Deactivate a Test Case instead of permanently deleting it.

    This is a soft delete.
    """

    if not test_case.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test case is already inactive",
        )

    test_case.is_active = False

    try:
        db.add(test_case)

        db.commit()

        db.refresh(test_case)

    except SQLAlchemyError as exc:
        db.rollback()

        logger.error("Test case database error on deactivate", exc_info=True)

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate test case",
        ) from exc

    return test_case


def get_test_case_with_parameters_or_404(
    db: Session,
    test_case_id: int,
) -> TestCase:
    """
    Get a Test Case by ID along with its associated parameters
    loaded via the SQLAlchemy relationship.
    """
    query = (
        select(TestCase)
        .where(TestCase.id == test_case_id)
        .options(selectinload(TestCase.parameters))
    )
    test_case = db.scalar(query)

    if test_case is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test case not found",
        )

    return test_case


def reactivate_test_case(
    db: Session,
    test_case: TestCase,
) -> TestCase:
    """
    Reactivate a Test Case.
    """
    if test_case.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test case is already active",
        )

    test_case.is_active = True

    try:
        db.add(test_case)
        db.commit()
        db.refresh(test_case)
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Test case database error on reactivate", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate test case",
        ) from exc

    return test_case