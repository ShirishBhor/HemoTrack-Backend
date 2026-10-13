from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.accounts import (
    AccountDateWiseSummary,
    DailyCollectionReport,
    PendingDuesLedger,
)
from app.services import accounts_service

router = APIRouter(prefix="/accounts", tags=["Accounts"])

AccountsViewUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]

AccountsAdminUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
        )
    ),
]


@router.get("/daily-collection", response_model=DailyCollectionReport)
def get_daily_collection_report(
    db: DbSession,
    _: AccountsViewUser,
    report_date: date | None = None,
):
    target = report_date or date.today()
    return accounts_service.get_daily_collection(db, target)


@router.get("/pending-dues", response_model=PendingDuesLedger)
def get_pending_dues_ledger(
    db: DbSession,
    _: AccountsViewUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    include_cancelled: bool = Query(default=False),
    start_date: date | None = None,
    end_date: date | None = None,
):
    return accounts_service.get_pending_dues_ledger(
        db,
        skip=skip,
        limit=limit,
        include_cancelled=include_cancelled,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/summary", response_model=AccountDateWiseSummary)
def get_account_summary(
    from_date: date,
    to_date: date,
    db: DbSession,
    _: AccountsAdminUser,
):
    return accounts_service.get_date_wise_summary(
        db,
        from_date=from_date,
        to_date=to_date,
    )
