from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.bill import Bill, BillStatus
from app.models.doctor import Doctor
from app.models.expense import Expense
from app.models.patient import Patient
from app.models.payment import Payment, PaymentMode
from app.models.refund import Refund
from app.schemas.accounts import (
    AccountDateWiseSummary,
    DailyCollectionReport,
    ModeCollectionSummary,
    PendingDueItem,
    PendingDuesLedger,
)


def get_daily_collection(db: Session, target_date: date) -> DailyCollectionReport:
    # Query actual payments received on target_date, grouped by payment_mode
    results = db.execute(
        select(
            Payment.payment_mode,
            func.count(Payment.id).label("cnt"),
            func.coalesce(func.sum(Payment.amount), Decimal("0.00")).label("total_amt"),
        )
        .where(func.date(Payment.payment_date) == target_date)
        .group_by(Payment.payment_mode)
    ).all()

    by_mode = []
    total_txns = 0
    total_collected = Decimal("0.00")

    found_modes = set()
    for row in results:
        mode_val = row.payment_mode.value if hasattr(row.payment_mode, "value") else str(row.payment_mode)
        cnt = int(row.cnt)
        amt = Decimal(str(row.total_amt)).quantize(Decimal("0.01"))

        by_mode.append(ModeCollectionSummary(payment_mode=mode_val, count=cnt, total_amount=amt))
        total_txns += cnt
        total_collected += amt
        found_modes.add(mode_val)

    # Include modes with 0 amount for completeness
    for pm in PaymentMode:
        if pm.value not in found_modes:
            by_mode.append(ModeCollectionSummary(payment_mode=pm.value, count=0, total_amount=Decimal("0.00")))

    by_mode.sort(key=lambda x: x.payment_mode)

    return DailyCollectionReport(
        report_date=target_date,
        generated_at=datetime.now(),
        total_transactions=total_txns,
        total_collected=total_collected.quantize(Decimal("0.01")),
        by_payment_mode=by_mode,
    )


def get_pending_dues_ledger(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 100,
    include_cancelled: bool = False,
    start_date: date | None = None,
    end_date: date | None = None,
) -> PendingDuesLedger:
    query = (
        select(Bill)
        .options(
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
        )
        .where(Bill.due_amount > Decimal("0.00"))
    )

    if not include_cancelled:
        query = query.where(Bill.is_cancelled.is_(False))
    if start_date is not None:
        query = query.where(func.date(Bill.created_at) >= start_date)
    if end_date is not None:
        query = query.where(func.date(Bill.created_at) <= end_date)

    # Calculate total summary
    sum_query = (
        select(
            func.count(Bill.id),
            func.coalesce(func.sum(Bill.due_amount), Decimal("0.00")),
        )
        .where(Bill.due_amount > Decimal("0.00"))
    )
    if not include_cancelled:
        sum_query = sum_query.where(Bill.is_cancelled.is_(False))
    if start_date is not None:
        sum_query = sum_query.where(func.date(Bill.created_at) >= start_date)
    if end_date is not None:
        sum_query = sum_query.where(func.date(Bill.created_at) <= end_date)

    total_count, total_dues = db.execute(sum_query).one()
    total_dues = Decimal(str(total_dues)).quantize(Decimal("0.01"))

    bills = db.scalars(query.order_by(Bill.due_amount.desc(), Bill.id.desc()).offset(skip).limit(limit)).all()

    items = []
    for b in bills:
        patient = b.patient
        doctor = b.doctor
        items.append(
            PendingDueItem(
                bill_id=b.id,
                bill_number=b.bill_number,
                bill_date=b.created_at,
                status=b.status,
                is_cancelled=b.is_cancelled,
                patient_id=patient.id,
                patient_uhid=patient.uhid,
                patient_name=patient.name,
                patient_phone=patient.phone,
                doctor_name=doctor.name if doctor else None,
                subtotal=b.subtotal,
                discount_amount=b.discount_amount,
                payable_amount=b.payable_amount,
                paid_amount=b.paid_amount,
                due_amount=b.due_amount,
            )
        )

    return PendingDuesLedger(
        total_bills_with_dues=total_count,
        total_outstanding_due=total_dues,
        items=items,
    )


def get_date_wise_summary(
    db: Session,
    *,
    from_date: date,
    to_date: date,
) -> AccountDateWiseSummary:
    # 1. Billed sales metrics (from Bills created in the period)
    sales_res = db.execute(
        select(
            func.count(Bill.id),
            func.coalesce(func.sum(Bill.subtotal), Decimal("0.00")),
            func.coalesce(func.sum(Bill.discount_amount), Decimal("0.00")),
            func.coalesce(func.sum(Bill.payable_amount), Decimal("0.00")),
            func.coalesce(func.sum(Bill.due_amount), Decimal("0.00")),
        )
        .where(func.date(Bill.created_at) >= from_date)
        .where(func.date(Bill.created_at) <= to_date)
        .where(Bill.is_cancelled.is_(False))
    ).one()

    bill_cnt = int(sales_res[0])
    subtotal_sum = Decimal(str(sales_res[1])).quantize(Decimal("0.01"))
    discount_sum = Decimal(str(sales_res[2])).quantize(Decimal("0.01"))
    net_sales_sum = Decimal(str(sales_res[3])).quantize(Decimal("0.01"))
    period_dues = Decimal(str(sales_res[4])).quantize(Decimal("0.01"))

    # 2. Payments collected in the period (by payment_date, independent of bill creation date)
    payments_sum = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), Decimal("0.00")))
        .where(func.date(Payment.payment_date) >= from_date)
        .where(func.date(Payment.payment_date) <= to_date)
    ) or Decimal("0.00")
    payments_sum = Decimal(str(payments_sum)).quantize(Decimal("0.01"))

    # 3. Expenses incurred in the period (by expense_date)
    expenses_sum = db.scalar(
        select(func.coalesce(func.sum(Expense.amount), Decimal("0.00")))
        .where(Expense.expense_date >= from_date)
        .where(Expense.expense_date <= to_date)
    ) or Decimal("0.00")
    expenses_sum = Decimal(str(expenses_sum)).quantize(Decimal("0.01"))

    # 4. Refunds issued in the period (by refund_date)
    refunds_sum = db.scalar(
        select(func.coalesce(func.sum(Refund.amount), Decimal("0.00")))
        .where(func.date(Refund.refund_date) >= from_date)
        .where(func.date(Refund.refund_date) <= to_date)
    ) or Decimal("0.00")
    refunds_sum = Decimal(str(refunds_sum)).quantize(Decimal("0.01"))

    # Net Cash Flow = Payments Collected - Expenses Incurred - Refunds Issued
    net_cash_flow = (payments_sum - expenses_sum - refunds_sum).quantize(Decimal("0.01"))

    return AccountDateWiseSummary(
        from_date=from_date,
        to_date=to_date,
        generated_at=datetime.now(),
        total_bills_created=bill_cnt,
        total_billed_sales=subtotal_sum,
        total_discounts_given=discount_sum,
        total_net_sales=net_sales_sum,
        total_payments_collected=payments_sum,
        total_expenses_incurred=expenses_sum,
        total_refunds_issued=refunds_sum,
        net_cash_flow=net_cash_flow,
        active_period_dues=period_dues,
    )
