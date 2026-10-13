from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.expense import Expense, ExpenseCategory, ExpensePaymentMode
from app.schemas.expense import ExpenseCreate


def generate_voucher_number(db: Session) -> str:
    current_year = date.today().year
    prefix = f"EXP-{current_year}-"

    latest = db.scalar(
        select(Expense)
        .where(Expense.voucher_number.like(f"{prefix}%"))
        .order_by(Expense.id.desc())
        .limit(1)
        .with_for_update()
    )
    if latest and latest.voucher_number.startswith(prefix):
        try:
            seq_num = int(latest.voucher_number.split("-")[-1]) + 1
        except ValueError:
            seq_num = (db.scalar(select(func.count(Expense.id))) or 0) + 1
    else:
        seq_num = (db.scalar(select(func.count(Expense.id))) or 0) + 1

    return f"{prefix}{seq_num:05d}"


def get_expense(db: Session, expense_id: int) -> Expense | None:
    return db.scalar(
        select(Expense)
        .options(joinedload(Expense.created_by_user))
        .where(Expense.id == expense_id)
    )


def list_expenses(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    category: ExpenseCategory | None = None,
    payment_mode: ExpensePaymentMode | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> list[Expense]:
    query = select(Expense).options(joinedload(Expense.created_by_user))

    if category is not None:
        query = query.where(Expense.category == category)
    if payment_mode is not None:
        query = query.where(Expense.payment_mode == payment_mode)
    if start_date is not None:
        query = query.where(Expense.expense_date >= start_date)
    if end_date is not None:
        query = query.where(Expense.expense_date <= end_date)

    return list(db.scalars(query.order_by(Expense.expense_date.desc(), Expense.id.desc()).offset(skip).limit(limit)).all())


def create_expense(db: Session, payload: ExpenseCreate, *, created_by_id: int) -> Expense:
    amount = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expense amount must be greater than zero",
        )

    voucher_number = generate_voucher_number(db)

    expense = Expense(
        voucher_number=voucher_number,
        category=payload.category,
        amount=amount,
        payment_mode=payload.payment_mode,
        expense_date=payload.expense_date,
        payee=payload.payee,
        description=payload.description,
        receipt_ref=payload.receipt_ref,
        created_by_id=created_by_id,
    )
    db.add(expense)
    db.commit()
    db.refresh(expense)
    return expense
