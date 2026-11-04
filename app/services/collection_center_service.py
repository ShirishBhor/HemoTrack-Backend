"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
Business logic for Collection Center management.

Handles:
- Listing and searching collection centers
- Creating, updating, deactivating, and reactivating collection centers
- Uniqueness validation for email and phone
"""

from datetime import date
from decimal import Decimal
import logging

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.bill import Bill
from app.models.collection_center import CollectionCenter
from app.models.patient import Patient
from app.schemas.collection_center import (
    CollectionCenterCreate,
    CollectionCenterStatsResponse,
    CollectionCenterUpdate,
    CommissionBillItem,
)

logger = logging.getLogger(__name__)


def get_collection_center(db: Session, center_id: int) -> CollectionCenter | None:
    return db.get(CollectionCenter, center_id)


def get_collection_center_or_404(db: Session, center_id: int) -> CollectionCenter:
    center = get_collection_center(db, center_id)
    if center is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Collection center not found",
        )
    return center


def count_collection_centers(
    db: Session,
    *,
    search: str | None = None,
    is_active: bool | None = None,
) -> int:
    """Return the total number of collection centers matching the given filters."""
    query = select(func.count(CollectionCenter.id))

    if isinstance(is_active, bool):
        query = query.where(CollectionCenter.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(CollectionCenter.name).like(pattern),
                func.lower(CollectionCenter.contact_person).like(pattern),
                func.lower(CollectionCenter.phone).like(pattern),
                func.lower(CollectionCenter.email).like(pattern),
                func.lower(CollectionCenter.address).like(pattern),
            )
        )

    return db.scalar(query) or 0


def list_collection_centers(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[CollectionCenter]:
    query = select(CollectionCenter)

    if isinstance(is_active, bool):
        query = query.where(CollectionCenter.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(CollectionCenter.name).like(pattern),
                func.lower(CollectionCenter.contact_person).like(pattern),
                func.lower(CollectionCenter.phone).like(pattern),
                func.lower(CollectionCenter.email).like(pattern),
                func.lower(CollectionCenter.address).like(pattern),
            )
        )

    query = query.order_by(CollectionCenter.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def _validate_collection_center_uniqueness(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    center_id: int | None = None,
) -> None:
    """Raise 409 if email or phone is already taken by another collection center."""
    if email is not None:
        email_query = select(CollectionCenter).where(
            func.lower(CollectionCenter.email) == email.lower()
        )
        if center_id is not None:
            email_query = email_query.where(CollectionCenter.id != center_id)
        if db.scalar(email_query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Collection center with this email already exists",
            )

    if phone is not None:
        phone_query = select(CollectionCenter).where(CollectionCenter.phone == phone)
        if center_id is not None:
            phone_query = phone_query.where(CollectionCenter.id != center_id)
        if db.scalar(phone_query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Collection center with this phone number already exists",
            )


def _commit_collection_center_changes(db: Session) -> None:
    """Commit the session, rolling back and raising on DB errors."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error("Collection center integrity error on commit", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Collection center data conflicts with an existing database record",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Collection center database error on commit", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save collection center data",
        ) from exc


def create_collection_center(db: Session, payload: CollectionCenterCreate) -> CollectionCenter:
    center_data = payload.model_dump()

    _validate_collection_center_uniqueness(
        db,
        email=center_data.get("email"),
        phone=center_data.get("phone"),
    )

    center = CollectionCenter(**center_data)
    db.add(center)
    _commit_collection_center_changes(db)
    db.refresh(center)
    return center


def update_collection_center(
    db: Session,
    center: CollectionCenter,
    payload: CollectionCenterUpdate,
) -> CollectionCenter:
    update_data = payload.model_dump(exclude_unset=True)

    _validate_collection_center_uniqueness(
        db,
        email=update_data.get("email"),
        phone=update_data.get("phone"),
        center_id=center.id,
    )

    for field, value in update_data.items():
        setattr(center, field, value)

    db.add(center)
    _commit_collection_center_changes(db)
    db.refresh(center)
    return center


def deactivate_collection_center(db: Session, center: CollectionCenter) -> CollectionCenter:
    """Soft-delete a collection center by setting is_active = False."""
    if not center.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection center is already inactive",
        )

    center.is_active = False
    db.add(center)
    _commit_collection_center_changes(db)
    db.refresh(center)
    return center


def reactivate_collection_center(db: Session, center: CollectionCenter) -> CollectionCenter:
    """Restore a previously deactivated collection center."""
    if center.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Collection center is already active",
        )

    center.is_active = True
    db.add(center)
    _commit_collection_center_changes(db)
    db.refresh(center)
    return center


def get_collection_center_stats(
    db: Session,
    center_id: int,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> CollectionCenterStatsResponse:
    """Calculate patient referrals, billings, and earned commission for a collection center."""
    center = get_collection_center_or_404(db, center_id)

    total_patients = (
        db.scalar(
            select(func.count(Patient.id)).where(
                Patient.collection_center_id == center_id
            )
        )
        or 0
    )

    query = (
        select(Bill, Patient)
        .join(Patient, Bill.patient_id == Patient.id)
        .where(
            Patient.collection_center_id == center_id,
            Bill.is_cancelled.is_(False),
        )
    )

    if from_date is not None:
        query = query.where(func.date(Bill.created_at) >= from_date)
    if to_date is not None:
        query = query.where(func.date(Bill.created_at) <= to_date)

    query = query.order_by(Bill.id.desc())
    results = db.execute(query).all()

    commission_percent = (
        Decimal(str(center.commission_percent))
        if center.commission_percent is not None
        else Decimal("0.00")
    )

    total_billed = Decimal("0.00")
    total_paid = Decimal("0.00")
    total_commission = Decimal("0.00")
    recent_bills: list[CommissionBillItem] = []

    for bill, patient in results:
        billed_amt = Decimal(str(bill.payable_amount))
        paid_amt = Decimal(str(bill.paid_amount))
        comm_amt = (
            billed_amt * commission_percent / Decimal("100.00")
        ).quantize(Decimal("0.01"))

        total_billed += billed_amt
        total_paid += paid_amt
        total_commission += comm_amt

        recent_bills.append(
            CommissionBillItem(
                bill_id=bill.id,
                bill_number=bill.bill_number,
                bill_date=bill.created_at,
                patient_id=patient.id,
                patient_name=patient.name,
                patient_uhid=patient.uhid,
                billed_amount=billed_amt,
                paid_amount=paid_amt,
                commission_percent=commission_percent,
                commission_amount=comm_amt,
                status=bill.status.value if hasattr(bill.status, "value") else str(bill.status),
            )
        )

    return CollectionCenterStatsResponse(
        center_id=center.id,
        center_name=center.name,
        commission_percent=commission_percent,
        total_patients=total_patients,
        total_bills=len(results),
        total_billed_amount=total_billed.quantize(Decimal("0.01")),
        total_paid_amount=total_paid.quantize(Decimal("0.01")),
        total_commission_earned=total_commission.quantize(Decimal("0.01")),
        recent_bills=recent_bills,
    )
