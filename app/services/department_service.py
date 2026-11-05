"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-22

Description:
Contains database operations and business logic
for Department management.
"""

import logging

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.department import Department
from app.schemas.department import (
    DepartmentCreate,
    DepartmentUpdate,
)

logger = logging.getLogger(__name__)


def get_department_or_404(
    db: Session,
    department_id: int,
) -> Department:
    department = db.get(Department, department_id)

    if department is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    return department


def list_departments(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Department]:
    query = select(Department)

    if isinstance(is_active, bool):
        query = query.where(Department.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(
            or_(
                Department.name.ilike(pattern),
                Department.code.ilike(pattern),
            )
        )

    safe_skip = skip if isinstance(skip, int) else 0
    safe_limit = limit if isinstance(limit, int) else 50
    query = (
        query.order_by(Department.name.asc())
        .offset(safe_skip)
        .limit(safe_limit)
    )

    return list(db.scalars(query).all())


def create_department(
    db: Session,
    payload: DepartmentCreate,
) -> Department:
    department = Department(
        name=payload.name,
        code=payload.code,
        description=payload.description,
    )

    try:
        db.add(department)
        db.commit()
        db.refresh(department)
        return department

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name or code already exists.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to create department")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create department.",
        ) from exc


def update_department(
    db: Session,
    department_id: int,
    payload: DepartmentUpdate,
) -> Department:
    department = get_department_or_404(db, department_id)

    changes = payload.model_dump(exclude_unset=True)

    if not changes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field is required for update.",
        )

    for field, value in changes.items():
        setattr(department, field, value)

    try:
        db.commit()
        db.refresh(department)
        return department

    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A department with this name or code already exists.",
        ) from exc

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to update department")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update department.",
        ) from exc


def update_department_status(
    db: Session,
    department_id: int,
    is_active: bool,
) -> Department:
    """Activate or deactivate a department."""
    if is_active:
        return reactivate_department(db, department_id)
    return deactivate_department(db, department_id)


def deactivate_department(
    db: Session,
    department_id: int,
) -> Department:
    department = get_department_or_404(db, department_id)

    if not department.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department is already inactive.",
        )

    department.is_active = False

    try:
        db.commit()
        db.refresh(department)
        return department

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to deactivate department")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate department.",
        ) from exc


def reactivate_department(
    db: Session,
    department_id: int,
) -> Department:
    department = get_department_or_404(db, department_id)

    if department.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Department is already active.",
        )

    department.is_active = True

    try:
        db.commit()
        db.refresh(department)
        return department

    except SQLAlchemyError as exc:
        db.rollback()
        logger.exception("Failed to reactivate department")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reactivate department.",
        ) from exc
