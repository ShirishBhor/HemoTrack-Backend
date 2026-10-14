from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.bill import Bill, BillStatus
from app.models.payment import Payment
from app.schemas.payment import PaymentCreate


def generate_receipt_number(db: Session) -> str:
    current_year = date.today().year
    prefix = f"RCP-{current_year}-"

    latest_payment = db.scalar(
        select(Payment)
        .where(Payment.receipt_number.like(f"{prefix}%"))
        .order_by(Payment.id.desc())
        .limit(1)
        .with_for_update()
    )
    if latest_payment and latest_payment.receipt_number.startswith(prefix):
        try:
            seq_num = int(latest_payment.receipt_number.split("-")[-1]) + 1
        except ValueError:
            seq_num = (db.scalar(select(func.count(Payment.id))) or 0) + 1
    else:
        seq_num = (db.scalar(select(func.count(Payment.id))) or 0) + 1

    return f"{prefix}{seq_num:05d}"


def get_payment(db: Session, payment_id: int) -> Payment | None:
    return db.scalar(
        select(Payment)
        .options(joinedload(Payment.received_by_user))
        .where(Payment.id == payment_id)
    )


def list_payments_for_bill(db: Session, bill_id: int) -> list[Payment]:
    return list(
        db.scalars(
            select(Payment)
            .options(joinedload(Payment.received_by_user))
            .where(Payment.bill_id == bill_id)
            .order_by(Payment.id.asc())
        ).all()
    )


def record_payment(db: Session, payload: PaymentCreate, *, received_by_id: int) -> Payment:
    # Validate payment amount is strictly positive
    pay_amount = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if pay_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment amount must be greater than zero",
        )

    # Lock Bill row for update to ensure safe concurrent balance deduction
    bill = db.scalar(
        select(Bill)
        .where(Bill.id == payload.bill_id)
        .with_for_update()
    )
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    if bill.is_cancelled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot record payment for a cancelled bill",
        )

    if bill.status == BillStatus.PAID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill is already fully paid",
        )

    # Server-side validation against current due_amount
    current_due = Decimal(str(bill.due_amount)).quantize(Decimal("0.01"))
    if pay_amount > current_due:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount (₹{pay_amount}) exceeds outstanding balance (₹{current_due})",
        )

    receipt_number = generate_receipt_number(db)

    payment = Payment(
        receipt_number=receipt_number,
        bill_id=bill.id,
        amount=pay_amount,
        payment_mode=payload.payment_mode,
        transaction_ref=payload.transaction_ref,
        notes=payload.notes,
        received_by_id=received_by_id,
    )
    db.add(payment)

    # Re-calculate paid_amount, due_amount, and status on server
    new_paid = (Decimal(str(bill.paid_amount)) + pay_amount).quantize(Decimal("0.01"))
    new_due = (current_due - pay_amount).quantize(Decimal("0.01"))

    bill.paid_amount = new_paid
    bill.due_amount = new_due

    if new_due == Decimal("0.00"):
        bill.status = BillStatus.PAID
    else:
        bill.status = BillStatus.PARTIALLY_PAID

    # Commit atomically
    db.commit()
    db.refresh(payment)
    return payment
