from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.deps import DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services import user_service

router = APIRouter(prefix="/users", tags=["users"])

AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


@router.get("", response_model=list[UserRead])
def list_users(
    db: DbSession,
    _: AdminUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    department: str | None = Query(default=None),
) -> list[User]:
    return user_service.list_users(db, skip=skip, limit=limit, department=department)


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreate,
    db: DbSession,
    _: AdminUser,
) -> User:
    return user_service.create_user(db, payload)


@router.get("/{user_id}", response_model=UserRead)
def get_user(
    user_id: int,
    db: DbSession,
    _: AdminUser,
) -> User:
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    payload: UserUpdate,
    db: DbSession,
    _: AdminUser,
) -> User:
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_service.update_user(db, user, payload)


@router.delete("/{user_id}", response_model=UserRead)
def deactivate_user(
    user_id: int,
    db: DbSession,
    admin_user: AdminUser,
) -> User:
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_service.deactivate_user(db, current_user_id=admin_user.id, target_user=user)


@router.post("/{user_id}/unlock", response_model=UserRead)
def unlock_user(
    user_id: int,
    db: DbSession,
    _: AdminUser,
) -> User:
    user = user_service.get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user_service.unlock_user(db, user)

