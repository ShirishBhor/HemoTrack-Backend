from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import create_access_token, hash_password, verify_password
from app.models.user import User, UserRole
from app.schemas.user import UserCreate, UserUpdate


def get_user_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(User.email == email))


def get_user_by_employee_code(db: Session, employee_code: str) -> User | None:
    return db.scalar(select(User).where(User.employee_code == employee_code))


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.get(User, user_id)


def authenticate_user(db: Session, email: str, password: str) -> User:
    user = get_user_by_email(db, email)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is locked due to multiple failed login attempts. Please contact an administrator.",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    if not verify_password(password, user.hashed_password):
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= 5:
            user.is_locked = True
        db.add(user)
        db.commit()
        if user.is_locked:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is locked due to multiple failed login attempts. Please contact an administrator.",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.failed_login_attempts = 0
    user.last_login_at = datetime.now(timezone.utc)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def create_access_token_for_user(user: User) -> str:
    return create_access_token(subject=user.id, extra_claims={"role": user.role.value})


def create_user(db: Session, payload: UserCreate) -> User:
    if get_user_by_email(db, payload.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    if payload.employee_code and get_user_by_employee_code(db, payload.employee_code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee code already registered",
        )
    user = User(
        email=payload.email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        phone=payload.phone,
        role=payload.role,
        employee_code=payload.employee_code,
        department=payload.department,
        profile_picture_url=payload.profile_picture_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def list_users(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    department: str | None = None,
) -> list[User]:
    query = select(User)
    if department:
        query = query.where(User.department == department)
    query = query.offset(skip).limit(limit)
    return list(db.scalars(query).all())


def update_user(db: Session, user: User, payload: UserUpdate) -> User:
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] != user.email:
        existing = get_user_by_email(db, data["email"])
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )
    if "employee_code" in data and data["employee_code"] != user.employee_code:
        if data["employee_code"] is not None:
            existing = get_user_by_employee_code(db, data["employee_code"])
            if existing and existing.id != user.id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Employee code already registered",
                )
    if "password" in data and data["password"]:
        data["hashed_password"] = hash_password(data.pop("password"))
    for field, value in data.items():
        setattr(user, field, value)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def deactivate_user(db: Session, current_user_id: int, target_user: User) -> User:
    if current_user_id == target_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Administrators cannot deactivate their own account",
        )
    target_user.is_active = False
    db.add(target_user)
    db.commit()
    db.refresh(target_user)
    return target_user


def unlock_user(db: Session, user: User) -> User:
    user.failed_login_attempts = 0
    user.is_locked = False
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def ensure_admin_exists(db: Session, email: str, password: str, full_name: str) -> User:
    existing = get_user_by_email(db, email)
    if existing:
        return existing
    user = User(
        email=email,
        hashed_password=hash_password(password),
        full_name=full_name,
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

