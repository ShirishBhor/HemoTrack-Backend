from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.bill import BillStatus
from app.models.user import User, UserRole
from app.schemas.bill import BillCancel, BillCreate, BillRead
from app.schemas.receipt import PrintableReceipt
from app.services import billing_service


router = APIRouter(prefix="/bills", tags=["Billing"])

BillWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]


@router.post("", response_model=BillRead, status_code=status.HTTP_201_CREATED)
def create_bill(
    payload: BillCreate,
    db: DbSession,
    current_user: BillWriteUser,
):
    return billing_service.create_bill(db, payload, created_by_id=current_user.id)


@router.get("", response_model=list[BillRead])
def list_bills(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status_filter: BillStatus | None = Query(default=None, alias="status"),
    start_date: date | None = None,
    end_date: date | None = None,
    include_cancelled: bool = Query(default=True),
):
    return billing_service.list_bills(
        db,
        skip=skip,
        limit=limit,
        search=search,
        patient_id=patient_id,
        doctor_id=doctor_id,
        status_filter=status_filter,
        start_date=start_date,
        end_date=end_date,
        include_cancelled=include_cancelled,
    )


BillAdminUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
        )
    ),
]


@router.get("/{bill_id}", response_model=BillRead)
def get_bill(
    bill_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return billing_service.get_bill_or_404(db, bill_id)


@router.get("/{bill_id}/receipt", response_model=PrintableReceipt)
def get_printable_receipt(
    bill_id: int,
    db: DbSession,
    _: CurrentUser,
):
    return billing_service.get_printable_receipt(db, bill_id)


@router.post("/{bill_id}/cancel", response_model=BillRead)
def cancel_bill(
    bill_id: int,
    payload: BillCancel,
    db: DbSession,
    current_user: BillAdminUser,
):
    return billing_service.cancel_bill(
        db,
        bill_id,
        cancelled_by_id=current_user.id,
        reason=payload.reason,
    )

