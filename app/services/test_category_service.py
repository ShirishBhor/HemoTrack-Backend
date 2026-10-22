
"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-22

Description:
Contains database operations and business logic
for Test Category management.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.test_category import TestCategory
from app.schemas.test_category import (
    TestCategoryCreate,
    TestCategoryUpdate,
)

logger = logging.getLogger(__name__)


def get_category_or_404(
    db: Session,
    category_id: int,
) -> TestCategory:
    category = db.get(TestCategory, category_id)

    if category is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Test category not found.",
        )

    return category


def list_categories(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    active_only: bool = True,
) -> list[TestCategory]:
    query = select(TestCategory)

    if active_only:
        query = query.where(TestCategory.is_active.is_(True))

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                TestCategory.name.ilike(pattern),
                TestCategory.code.ilike(pattern),
            )
        )

    query = (
        query.order_by(TestCategory.name.asc())
        .offset(skip)
        .limit(limit)
    )

    return list(db.scalars(query).all())


def create_category(
    db: Session,
    payload: TestCategoryCreate,
) -> TestCategory:
    category = TestCategory(
        name=payload.name,
        code=payload.code,
        description=payload.description,
    )

    try:
        db.add(category)
        db.commit()
        db.refresh(category)
        return category

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name or code already exists.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to create test category")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create test category.",
        ) from exc


def update_category(
    db: Session,
    category_id: int,
    payload: TestCategoryUpdate,
) -> TestCategory:
    category = get_category_or_404(db, category_id)

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required for update.",
        )

    for field, value in changes.items():
        setattr(category, field, value)

    try:
        db.commit()
        db.refresh(category)
        return category

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A category with this name or code already exists.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to update test category")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update test category.",
        ) from exc


def deactivate_category(
    db: Session,
    category_id: int,
) -> TestCategory:
    category = get_category_or_404(db, category_id)

    if not category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test category is already inactive.",
        )

    category.is_active = False

    try:
        db.commit()
        db.refresh(category)
        return category

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to deactivate test category")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate test category.",
        ) from exc


def reactivate_category(
    db: Session,
    category_id: int,
) -> TestCategory:
    category = get_category_or_404(db, category_id)

    if category.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Test category is already active.",
        )

    category.is_active = True

    try:
        db.commit()
        db.refresh(category)
        return category

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to reactivate test category")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate test category.",
        ) from exc
