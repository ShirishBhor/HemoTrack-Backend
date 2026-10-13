from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.test import TestCategory, TestMaster
from app.schemas.test import (
    TestCategoryCreate,
    TestCategoryUpdate,
    TestMasterCreate,
    TestMasterUpdate,
)


def list_categories(db: Session, *, include_inactive: bool = False) -> list[TestCategory]:
    query = select(TestCategory)
    if not include_inactive:
        query = query.where(TestCategory.is_active.is_(True))
    return list(db.scalars(query.order_by(TestCategory.name)).all())


def get_category_by_id(db: Session, category_id: int) -> TestCategory | None:
    return db.get(TestCategory, category_id)


def create_category(db: Session, payload: TestCategoryCreate) -> TestCategory:
    existing = db.scalar(select(TestCategory).where(func.lower(TestCategory.name) == payload.name.lower()))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Category with name '{payload.name}' already exists",
        )
    category = TestCategory(
        name=payload.name,
        description=payload.description,
        is_active=payload.is_active,
    )
    db.add(category)
    db.commit()
    db.refresh(category)
    return category


def update_category(db: Session, category_id: int, payload: TestCategoryUpdate) -> TestCategory:
    category = get_category_by_id(db, category_id)
    if not category:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Category not found")

    if payload.name is not None and payload.name.lower() != category.name.lower():
        existing = db.scalar(select(TestCategory).where(func.lower(TestCategory.name) == payload.name.lower()))
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Category with name '{payload.name}' already exists",
            )
        category.name = payload.name

    if payload.description is not None:
        category.description = payload.description
    if payload.is_active is not None:
        category.is_active = payload.is_active

    db.commit()
    db.refresh(category)
    return category


def list_tests(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    category_id: int | None = None,
    include_inactive: bool = False,
) -> list[TestMaster]:
    query = select(TestMaster).options(joinedload(TestMaster.category))
    if not include_inactive:
        query = query.where(TestMaster.is_active.is_(True))
    if category_id is not None:
        query = query.where(TestMaster.category_id == category_id)
    if search:
        search_pattern = f"%{search.strip()}%"
        query = query.where(
            (TestMaster.name.ilike(search_pattern)) | (TestMaster.test_code.ilike(search_pattern))
        )

    return list(db.scalars(query.order_by(TestMaster.name).offset(skip).limit(limit)).all())


def get_test_by_id(db: Session, test_id: int) -> TestMaster | None:
    return db.scalar(
        select(TestMaster).options(joinedload(TestMaster.category)).where(TestMaster.id == test_id)
    )


def get_test_by_code(db: Session, test_code: str) -> TestMaster | None:
    return db.scalar(
        select(TestMaster)
        .options(joinedload(TestMaster.category))
        .where(TestMaster.test_code == test_code.strip().upper())
    )


def create_test(db: Session, payload: TestMasterCreate) -> TestMaster:
    code = payload.test_code.strip().upper()
    existing = get_test_by_code(db, code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Test with code '{code}' already exists",
        )

    if payload.category_id is not None:
        category = get_category_by_id(db, payload.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced category does not exist",
            )
        if not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced category is inactive",
            )

    test = TestMaster(
        category_id=payload.category_id,
        test_code=code,
        name=payload.name,
        price=payload.price,
        sample_type=payload.sample_type,
        turnaround_time_hours=payload.turnaround_time_hours,
        is_active=payload.is_active,
    )
    db.add(test)
    db.commit()
    db.refresh(test)
    return test


def update_test(db: Session, test_id: int, payload: TestMasterUpdate) -> TestMaster:
    test = get_test_by_id(db, test_id)
    if not test:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")

    if payload.test_code is not None:
        code = payload.test_code.strip().upper()
        if code != test.test_code:
            existing = get_test_by_code(db, code)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Test with code '{code}' already exists",
                )
            test.test_code = code

    if payload.category_id is not None:
        category = get_category_by_id(db, payload.category_id)
        if not category or not category.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referenced category does not exist or is inactive",
            )
        test.category_id = payload.category_id

    if payload.name is not None:
        test.name = payload.name
    if payload.price is not None:
        test.price = payload.price
    if payload.sample_type is not None:
        test.sample_type = payload.sample_type
    if payload.turnaround_time_hours is not None:
        test.turnaround_time_hours = payload.turnaround_time_hours
    if payload.is_active is not None:
        test.is_active = payload.is_active

    db.commit()
    db.refresh(test)
    return test
