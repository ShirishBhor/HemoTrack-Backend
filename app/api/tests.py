from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.test import (
    TestCategoryCreate,
    TestCategoryRead,
    TestCategoryUpdate,
    TestMasterCreate,
    TestMasterRead,
    TestMasterUpdate,
)
from app.services import test_service

router = APIRouter(prefix="/tests", tags=["Test Catalog"])

TestManageUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
]


# Categories
@router.get("/categories", response_model=list[TestCategoryRead])
def list_categories(
    db: DbSession,
    _: CurrentUser,
    include_inactive: bool = Query(default=False),
):
    return test_service.list_categories(db, include_inactive=include_inactive)


@router.post("/categories", response_model=TestCategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    payload: TestCategoryCreate,
    db: DbSession,
    _: TestManageUser,
):
    return test_service.create_category(db, payload)


@router.patch("/categories/{category_id}", response_model=TestCategoryRead)
def update_category(
    category_id: int,
    payload: TestCategoryUpdate,
    db: DbSession,
    _: TestManageUser,
):
    return test_service.update_category(db, category_id, payload)


# Tests
@router.get("", response_model=list[TestMasterRead])
def list_tests(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
    category_id: int | None = None,
    include_inactive: bool = Query(default=False),
):
    return test_service.list_tests(
        db,
        skip=skip,
        limit=limit,
        search=search,
        category_id=category_id,
        include_inactive=include_inactive,
    )


@router.post("", response_model=TestMasterRead, status_code=status.HTTP_201_CREATED)
def create_test(
    payload: TestMasterCreate,
    db: DbSession,
    _: TestManageUser,
):
    return test_service.create_test(db, payload)


@router.get("/{test_id}", response_model=TestMasterRead)
def get_test(
    test_id: int,
    db: DbSession,
    _: CurrentUser,
):
    test = test_service.get_test_by_id(db, test_id)
    if not test:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Test not found")
    return test


@router.patch("/{test_id}", response_model=TestMasterRead)
def update_test(
    test_id: int,
    payload: TestMasterUpdate,
    db: DbSession,
    _: TestManageUser,
):
    return test_service.update_test(db, test_id, payload)
