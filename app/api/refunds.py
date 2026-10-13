from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.refund import RefundCreate, RefundRead
from app.services import refund_service

router = APIRouter(prefix="/refunds", tags=["Refunds"])

RefundAdminUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
        )
    ),
]


@router.post("", response_model=RefundRead, status_code=status.HTTP_201_CREATED)
def issue_refund(
    payload: RefundCreate,
    db: DbSession,
    current_user: RefundAdminUser,
):
    return refund_service.process_refund(db, payload, processed_by_id=current_user.id)


@router.get("/bill/{bill_id}", response_model=list[RefundRead])
def list_refunds_for_bill(
    bill_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return refund_service.list_refunds_for_bill(db, bill_id)


@router.get("/{refund_id}", response_model=RefundRead)
def get_refund(
    refund_id: int,
    db: DbSession,
    _: CurrentUser,
):
    refund = refund_service.get_refund(db, refund_id)
    if not refund:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Refund not found")
    return refund
