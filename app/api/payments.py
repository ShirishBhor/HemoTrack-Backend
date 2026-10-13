from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.payment import PaymentCreate, PaymentRead
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])

PaymentWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]


@router.post("", response_model=PaymentRead, status_code=status.HTTP_201_CREATED)
def record_payment(
    payload: PaymentCreate,
    db: DbSession,
    current_user: PaymentWriteUser,
):
    return payment_service.record_payment(db, payload, received_by_id=current_user.id)


@router.get("/bill/{bill_id}", response_model=list[PaymentRead])
def list_payments_for_bill(
    bill_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return payment_service.list_payments_for_bill(db, bill_id)


@router.get("/{payment_id}", response_model=PaymentRead)
def get_payment(
    payment_id: int,
    db: DbSession,
    _: CurrentUser,
):
    payment = payment_service.get_payment(db, payment_id)
    if not payment:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payment
