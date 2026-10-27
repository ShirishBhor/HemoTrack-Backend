
from datetime import date, datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app.models.bill import Bill, BillItem, BillStatus, DiscountType
from app.models.doctor import Doctor
from app.models.patient import Patient
from app.models.test_case import TestCase
from app.schemas.bill import BillCreate


def generate_bill_number(db: Session) -> str:
    current_year = date.today().year
    prefix = f"BILL-{current_year}-"

    latest_bill = db.scalar(
        select(Bill)
        .where(Bill.bill_number.like(f"{prefix}%"))
        .order_by(Bill.id.desc())
        .limit(1)
        .with_for_update()
    )

    if latest_bill and latest_bill.bill_number.startswith(prefix):
        try:
            seq_num = int(latest_bill.bill_number.split("-")[-1]) + 1
        except ValueError:
            seq_num = (db.scalar(select(func.count(Bill.id))) or 0) + 1
    else:
        seq_num = (db.scalar(select(func.count(Bill.id))) or 0) + 1

    return f"{prefix}{seq_num:05d}"


def get_bill(db: Session, bill_id: int) -> Bill | None:
    return db.scalars(
        select(Bill)
        .options(
            joinedload(Bill.patient),
            joinedload(Bill.doctor),
            joinedload(Bill.created_by_user),
            joinedload(Bill.cancelled_by_user),
            joinedload(Bill.items),
            joinedload(Bill.payments),
        )
        .where(Bill.id == bill_id)
    ).unique().first()


def get_bill_or_404(db: Session, bill_id: int) -> Bill:
    bill = get_bill(db, bill_id)

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )

    return bill


def list_bills(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    patient_id: int | None = None,
    doctor_id: int | None = None,
    status_filter: BillStatus | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    include_cancelled: bool = True,
) -> list[Bill]:

    query = select(Bill).options(
        joinedload(Bill.patient),
        joinedload(Bill.doctor),
        joinedload(Bill.created_by_user),
        joinedload(Bill.items),
        joinedload(Bill.payments),
    )

    if not include_cancelled:
        query = query.where(Bill.is_cancelled.is_(False))

    if patient_id is not None:
        query = query.where(Bill.patient_id == patient_id)

    if doctor_id is not None:
        query = query.where(Bill.doctor_id == doctor_id)

    if status_filter is not None:
        query = query.where(Bill.status == status_filter)

    if start_date is not None:
        query = query.where(func.date(Bill.created_at) >= start_date)

    if end_date is not None:
        query = query.where(func.date(Bill.created_at) <= end_date)

    if search:
        search_pattern = f"%{search.strip()}%"

        query = query.join(Bill.patient).where(
            (Bill.bill_number.ilike(search_pattern))
            | (Patient.name.ilike(search_pattern))
            | (Patient.uhid.ilike(search_pattern))
        )

    # FIX: unique() is required for joined collection relationships.
    bills = db.scalars(
        query.order_by(Bill.id.desc())
        .offset(skip)
        .limit(limit)
    ).unique().all()

    return list(bills)


def create_bill(
    db: Session,
    payload: BillCreate,
    *,
    created_by_id: int,
) -> Bill:

    # 1. Validate Patient
    patient = db.get(Patient, payload.patient_id)

    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    if patient.is_cancelled or not patient.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot bill inactive or cancelled patient",
        )

    # 2. Validate Doctor (if specified)
    if payload.doctor_id is not None:
        doctor = db.get(Doctor, payload.doctor_id)

        if not doctor or not doctor.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Referred doctor not found or inactive",
            )

    # 3. Validate Test Items & Snapshot Values
    if not payload.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one test item is required",
        )

    test_ids = [item.test_id for item in payload.items]

    tests_db = db.scalars(
        select(TestCase).where(TestCase.id.in_(test_ids))
    ).all()

    test_map = {test.id: test for test in tests_db}

    bill_items_to_create = []
    subtotal = Decimal("0.00")

    for item_input in payload.items:
        test = test_map.get(item_input.test_id)

        if not test:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Test with ID {item_input.test_id} does not exist",
            )

        if not test.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Test '{test.name}' ({test.code}) "
                    "is currently inactive"
                ),
            )

        unit_price = Decimal(str(test.price)).quantize(
            Decimal("0.01")
        )

        qty = item_input.quantity
        gross_item = (unit_price * qty).quantize(
            Decimal("0.01")
        )

        item_disc = Decimal(
            str(item_input.discount_amount)
        ).quantize(Decimal("0.01"))

        if item_disc > gross_item:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Item discount (₹{item_disc}) exceeds "
                    f"item gross total (₹{gross_item}) "
                    f"for test '{test.name}'"
                ),
            )

        line_total = (gross_item - item_disc).quantize(
            Decimal("0.01")
        )

        subtotal += line_total

        bill_item = BillItem(
            test_id=test.id,
            test_name=test.name,
            test_code=test.code,
            unit_price=unit_price,
            quantity=qty,
            discount_amount=item_disc,
            line_total=line_total,
        )

        bill_items_to_create.append(bill_item)

    # 4. Calculate Overall Discounts and Payable
    subtotal = subtotal.quantize(Decimal("0.01"))

    discount_val = Decimal(
        str(payload.discount_value)
    ).quantize(Decimal("0.01"))

    overall_discount_amount = Decimal("0.00")

    if payload.discount_type == DiscountType.PERCENTAGE:
        if discount_val > Decimal("100.00") or discount_val < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Percentage discount must be between 0 and 100",
            )

        overall_discount_amount = (
            subtotal * (discount_val / Decimal("100.00"))
        ).quantize(Decimal("0.01"))

    elif payload.discount_type == DiscountType.FLAT:
        if discount_val < Decimal("0.00"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flat discount cannot be negative",
            )

        if discount_val > subtotal:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Flat discount cannot exceed bill subtotal",
            )

        overall_discount_amount = discount_val

    else:
        overall_discount_amount = Decimal("0.00")

    payable_amount = (
        subtotal - overall_discount_amount
    ).quantize(Decimal("0.01"))

    paid_amount = Decimal("0.00")
    due_amount = payable_amount

    # 5. Generate Bill Number
    bill_number = generate_bill_number(db)

    # 6. Save Bill
    bill = Bill(
        bill_number=bill_number,
        patient_id=payload.patient_id,
        doctor_id=payload.doctor_id,
        created_by_id=created_by_id,
        status=BillStatus.UNPAID,
        subtotal=subtotal,
        discount_type=payload.discount_type,
        discount_value=discount_val,
        discount_amount=overall_discount_amount,
        discount_reason=payload.discount_reason,
        payable_amount=payable_amount,
        paid_amount=paid_amount,
        due_amount=due_amount,
        remarks=payload.remarks,
        items=bill_items_to_create,
    )

    db.add(bill)
    db.commit()
    db.refresh(bill)

    return get_bill_or_404(db, bill.id)


def cancel_bill(
    db: Session,
    bill_id: int,
    *,
    cancelled_by_id: int,
    reason: str,
) -> Bill:

    bill = db.scalar(
        select(Bill)
        .where(Bill.id == bill_id)
        .with_for_update()
    )

    if not bill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bill not found",
        )

    if bill.is_cancelled or bill.status == BillStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bill has already been cancelled",
        )

    # Soft cancellation: preserve items, amounts, and payments
    bill.is_cancelled = True
    bill.status = BillStatus.CANCELLED
    bill.cancelled_at = datetime.now()
    bill.cancelled_by_id = cancelled_by_id
    bill.cancellation_reason = reason.strip()

    db.commit()
    db.refresh(bill)

    return get_bill_or_404(db, bill.id)


def get_printable_receipt(db: Session, bill_id: int) -> dict:
    bill = get_bill_or_404(db, bill_id)

    # Patient metadata
    patient = bill.patient

    patient_info = {
        "id": patient.id,
        "uhid": patient.uhid,
        "name": patient.name,
        "gender": (
            patient.gender.value
            if hasattr(patient.gender, "value")
            else str(patient.gender)
        ),
        "age_years": patient.age_years,
        "age_months": patient.age_months,
        "age_days": patient.age_days,
        "phone": patient.phone,
        "email": patient.email,
        "address": patient.address,
        "collection_center_name": (
            patient.collection_center.name
            if patient.collection_center
            else None
        ),
        "agent_name": (
            patient.agent.name
            if patient.agent
            else None
        ),
    }

    # Doctor metadata
    doctor_info = None

    if bill.doctor:
        doctor_info = {
            "id": bill.doctor.id,
            "name": bill.doctor.name,
            "specialization": bill.doctor.specialization,
            "phone": bill.doctor.phone,
        }

    # Items
    items_list = [
        {
            "id": item.id,
            "test_code": item.test_code,
            "test_name": item.test_name,
            "unit_price": item.unit_price,
            "quantity": item.quantity,
            "discount_amount": item.discount_amount,
            "line_total": item.line_total,
        }
        for item in bill.items
    ]

    # Payments ledger
    payments_list = [
        {
            "receipt_number": payment.receipt_number,
            "amount": payment.amount,
            "payment_mode": payment.payment_mode,
            "transaction_ref": payment.transaction_ref,
            "payment_date": payment.payment_date,
            "received_by_name": (
                payment.received_by_user.full_name
                if payment.received_by_user
                else None
            ),
        }
        for payment in bill.payments
    ]

    billed_by_name = (
        bill.created_by_user.full_name
        if bill.created_by_user
        else "System"
    )

    cancelled_by_name = (
        bill.cancelled_by_user.full_name
        if bill.cancelled_by_user
        else None
    )

    return {
        "bill_id": bill.id,
        "bill_number": bill.bill_number,
        "bill_date": bill.created_at,
        "status": bill.status,
        "is_cancelled": bill.is_cancelled,
        "cancellation_reason": bill.cancellation_reason,
        "cancelled_at": bill.cancelled_at,
        "cancelled_by_name": cancelled_by_name,
        "patient": patient_info,
        "doctor": doctor_info,
        "billed_by_name": billed_by_name,
        "items": items_list,
        "subtotal": bill.subtotal,
        "discount_type": bill.discount_type,
        "discount_value": bill.discount_value,
        "discount_amount": bill.discount_amount,
        "discount_reason": bill.discount_reason,
        "payable_amount": bill.payable_amount,
        "paid_amount": bill.paid_amount,
        "due_amount": bill.due_amount,
        "remarks": bill.remarks,
        "payments": payments_list,
        "generated_at": datetime.now(),
    }
