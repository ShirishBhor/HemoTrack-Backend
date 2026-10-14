from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.bill import Bill
from app.models.payment import Payment
from app.models.refund import Refund
from app.schemas.refund import RefundCreate


def generate_refund_number(db: Session) -> str:
    current_year = date.today().year
    prefix = f"REF-{current_year}-"

    latest = db.scalar(
        select(Refund)
        .where(Refund.refund_number.like(f"{prefix}%"))
        .order_by(Refund.id.desc())
        .limit(1)
        .with_for_update()
    )
    if latest and latest.refund_number.startswith(prefix):
        try:
            seq_num = int(latest.refund_number.split("-")[-1]) + 1
        except ValueError:
            seq_num = (db.scalar(select(func.count(Refund.id))) or 0) + 1
    else:
        seq_num = (db.scalar(select(func.count(Refund.id))) or 0) + 1

    return f"{prefix}{seq_num:05d}"


def get_refund(db: Session, refund_id: int) -> Refund | None:
    return db.scalar(
        select(Refund)
        .options(joinedload(Refund.processed_by_user))
        .where(Refund.id == refund_id)
    )


def list_refunds_for_bill(db: Session, bill_id: int) -> list[Refund]:
    return list(
        db.scalars(
            select(Refund)
            .options(joinedload(Refund.processed_by_user))
            .where(Refund.bill_id == bill_id)
            .order_by(Refund.id.asc())
        ).all()
    )


def process_refund(db: Session, payload: RefundCreate, *, processed_by_id: int) -> Refund:
    refund_amount = Decimal(str(payload.amount)).quantize(Decimal("0.01"))
    if refund_amount <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Refund amount must be greater than zero",
        )

    # Lock Bill row for update to ensure accurate refund headroom calculation
    bill = db.scalar(
        select(Bill)
        .where(Bill.id == payload.bill_id)
        .with_for_update()
    )
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")

    # Sum of all historically collected payments for this bill
    total_paid = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(Payment.bill_id == bill.id)
    ) or Decimal("0.00")
    total_paid = Decimal(str(total_paid)).quantize(Decimal("0.01"))

    if total_paid <= Decimal("0.00"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot refund a bill with zero collected payments",
        )

    # Sum of already issued refunds
    existing_refunds_sum = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), Decimal("0.00")))
        .where(Refund.bill_id == bill.id)
    ) or Decimal("0.00")
    existing_refunds_sum = Decimal(str(existing_refunds_sum)).quantize(Decimal("0.01"))

    refundable_balance = (total_paid - existing_refunds_sum).quantize(Decimal("0.01"))
    if refund_amount > refundable_balance:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Refund amount (₹{refund_amount}) exceeds refundable balance (₹{refundable_balance})",
        )

    refund_number = generate_refund_number(db)

    refund = Refund(
        refund_number=refund_number,
        bill_id=bill.id,
        amount=refund_amount,
        refund_mode=payload.refund_mode,
        reason=payload.reason.strip(),
        transaction_ref=payload.transaction_ref,
        processed_by_id=processed_by_id,
        refund_date=datetime.now(),
    )
    db.add(refund)
    db.commit()
    db.refresh(refund)
    return refund
