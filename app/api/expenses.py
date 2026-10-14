from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.expense import ExpenseCategory, ExpensePaymentMode
from app.models.user import User, UserRole
from app.schemas.expense import ExpenseCreate, ExpenseRead
from app.services import expense_service

router = APIRouter(prefix="/expenses", tags=["Expenses"])

ExpenseManageUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
        )
    ),
]


@router.post("", response_model=ExpenseRead, status_code=status.HTTP_201_CREATED)
def record_expense(
    payload: ExpenseCreate,
    db: DbSession,
    current_user: ExpenseManageUser,
):
    return expense_service.create_expense(db, payload, created_by_id=current_user.id)


@router.get("", response_model=list[ExpenseRead])
def list_expenses(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    category: ExpenseCategory | None = None,
    payment_mode: ExpensePaymentMode | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
):
    return expense_service.list_expenses(
        db,
        skip=skip,
        limit=limit,
        category=category,
        payment_mode=payment_mode,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/{expense_id}", response_model=ExpenseRead)
def get_expense(
    expense_id: int,
    db: DbSession,
    _: CurrentUser,
):
    expense = expense_service.get_expense(db, expense_id)
    if not expense:
        from fastapi import HTTPException
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Expense not found")
    return expense
