"""
Author: Nikhil Yuvraj Mole
Date: 2026-11-02

Description:
Service layer containing business logic for Package Master management.
Handles:
- Creating health packages with associated test cases
- Reading and searching packages
- Updating package metadata and test mappings
- Deactivating and reactivating packages
"""

import logging
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.department import Department
from app.models.package import Package, PackageTestCase
from app.models.test_case import TestCase
from app.schemas.package import PackageCreate, PackageUpdate

logger = logging.getLogger(__name__)


def _package_options():
    return [
        selectinload(Package.department),
        selectinload(Package.package_tests).selectinload(PackageTestCase.test_case),
    ]


def get_package(db: Session, package_id: int) -> Package | None:
    """Get a package by ID with related department and test cases."""
    stmt = (
        select(Package)
        .options(*_package_options())
        .where(Package.id == package_id)
    )
    return db.scalars(stmt).unique().first()


def get_package_or_404(db: Session, package_id: int) -> Package:
    """Get a package by ID or raise HTTP 404."""
    pkg = get_package(db, package_id)
    if pkg is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Package not found",
        )
    return pkg


def list_packages(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    active_only: bool = True,
    department_id: int | None = None,
) -> list[Package]:
    """
    List packages with pagination, search, and active/department filtering.
    """
    query = select(Package).options(*_package_options())

    if bool(active_only):
        query = query.where(Package.is_active.is_(True))

    if search and isinstance(search, str):
        search_term = f"%{search.strip()}%"
        query = query.where(
            or_(
                Package.name.ilike(search_term),
                Package.code.ilike(search_term),
            )
        )

    if department_id is not None and isinstance(department_id, int):
        query = query.where(Package.department_id == department_id)

    safe_skip = skip if isinstance(skip, int) else 0
    safe_limit = limit if isinstance(limit, int) else 50
    query = query.order_by(Package.name.asc()).offset(safe_skip).limit(safe_limit)
    return db.scalars(query).unique().all()


def _validate_test_cases(db: Session, test_case_ids: list[int]) -> list[TestCase]:
    """Validate that all provided test case IDs exist and are active."""
    if not test_case_ids:
        return []

    # Check for duplicates in input
    if len(test_case_ids) != len(set(test_case_ids)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Duplicate test cases provided in the package",
        )

    tests = db.scalars(
        select(TestCase).where(TestCase.id.in_(test_case_ids))
    ).all()

    found_map = {t.id: t for t in tests}
    missing_ids = [tid for tid in test_case_ids if tid not in found_map]
    if missing_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Test cases not found with IDs: {missing_ids}",
        )

    inactive_tests = [found_map[tid].name for tid in test_case_ids if not found_map[tid].is_active]
    if inactive_tests:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot add inactive test cases to package: {', '.join(inactive_tests)}",
        )

    return [found_map[tid] for tid in test_case_ids]


def _validate_department(db: Session, department_id: int | None) -> None:
    """Validate that department exists and is active."""
    if department_id is None:
        return

    dept = db.get(Department, department_id)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Department with ID {department_id} not found",
        )
    if not dept.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department '{dept.name}' is inactive",
        )


def create_package(db: Session, payload: PackageCreate) -> Package:
    """Create a new package and link its test cases."""
    # Check duplicate code
    existing = db.scalar(
        select(Package).where(Package.code == payload.code.upper())
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Package with code '{payload.code.upper()}' already exists",
        )

    # Validate department
    _validate_department(db, payload.department_id)

    # Validate tests
    _validate_test_cases(db, payload.test_case_ids)

    new_package = Package(
        name=payload.name,
        code=payload.code.upper(),
        description=payload.description,
        price=Decimal(str(payload.price)).quantize(Decimal("0.01")),
        tat=payload.tat,
        sample_requirements=payload.sample_requirements,
        fasting_required=payload.fasting_required,
        department_id=payload.department_id,
        is_active=True,
    )

    for order_idx, test_id in enumerate(payload.test_case_ids, start=1):
        new_package.package_tests.append(
            PackageTestCase(
                test_case_id=test_id,
                display_order=order_idx,
            )
        )

    db.add(new_package)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error("Database integrity error creating package: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to create package due to database constraint",
        )

    return get_package_or_404(db, new_package.id)


def update_package(
    db: Session,
    package_id: int,
    payload: PackageUpdate,
) -> Package:
    """Update package details and associated tests."""
    package = get_package_or_404(db, package_id)

    update_data = payload.model_dump(exclude_unset=True)

    # Check code uniqueness if changing
    if "code" in update_data and update_data["code"] is not None:
        code_upper = update_data["code"].upper()
        if code_upper != package.code:
            existing = db.scalar(
                select(Package).where(Package.code == code_upper)
            )
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Package with code '{code_upper}' already exists",
                )
            package.code = code_upper

    # Check department if changing
    if "department_id" in update_data:
        _validate_department(db, update_data["department_id"])
        package.department_id = update_data["department_id"]

    # Update simple scalar fields
    for field in ("name", "description", "tat", "sample_requirements", "fasting_required", "is_active"):
        if field in update_data and update_data[field] is not None:
            setattr(package, field, update_data[field])

    if "price" in update_data and update_data["price"] is not None:
        package.price = Decimal(str(update_data["price"])).quantize(Decimal("0.01"))

    # Update test case associations if provided
    if "test_case_ids" in update_data and update_data["test_case_ids"] is not None:
        _validate_test_cases(db, update_data["test_case_ids"])
        
        # Clear existing associations and flush deletes first to avoid unique constraint collisions
        package.package_tests.clear()
        db.flush()

        for order_idx, test_id in enumerate(update_data["test_case_ids"], start=1):
            package.package_tests.append(
                PackageTestCase(
                    package_id=package.id,
                    test_case_id=test_id,
                    display_order=order_idx,
                )
            )

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error("Database integrity error updating package %d: %s", package_id, exc)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to update package due to database constraint",
        )

    return get_package_or_404(db, package.id)


def deactivate_package(db: Session, package_id: int) -> Package:
    """Soft-delete a package by setting is_active=False."""
    package = get_package_or_404(db, package_id)
    package.is_active = False
    db.commit()
    return get_package_or_404(db, package.id)


def reactivate_package(db: Session, package_id: int) -> Package:
    """Reactivate a previously deactivated package."""
    package = get_package_or_404(db, package_id)
    package.is_active = True
    db.commit()
    return get_package_or_404(db, package.id)
