"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
Business logic for Agent management.

Handles:
- Listing and searching agents
- Creating, updating, deactivating, and reactivating agents
- Uniqueness validation for email and phone
"""

from datetime import date
from decimal import Decimal
import logging

from fastapi import HTTPException, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.bill import Bill
from app.models.patient import Patient
from app.schemas.agent import (
    AgentCreate,
    AgentStatsResponse,
    AgentUpdate,
    CommissionBillItem,
)

logger = logging.getLogger(__name__)


def get_agent(db: Session, agent_id: int) -> Agent | None:
    return db.get(Agent, agent_id)


def get_agent_or_404(db: Session, agent_id: int) -> Agent:
    agent = get_agent(db, agent_id)
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )
    return agent


def count_agents(
    db: Session,
    *,
    search: str | None = None,
    is_active: bool | None = None,
) -> int:
    """Return the total number of agents matching the given filters."""
    query = select(func.count(Agent.id))

    if isinstance(is_active, bool):
        query = query.where(Agent.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Agent.name).like(pattern),
                func.lower(Agent.phone).like(pattern),
                func.lower(Agent.email).like(pattern),
                func.lower(Agent.address).like(pattern),
            )
        )

    return db.scalar(query) or 0


def list_agents(
    db: Session,
    *,
    skip: int = 0,
    limit: int = 50,
    search: str | None = None,
    is_active: bool | None = None,
) -> list[Agent]:
    query = select(Agent)

    if isinstance(is_active, bool):
        query = query.where(Agent.is_active.is_(is_active))

    if search and search.strip():
        pattern = f"%{search.strip().lower()}%"
        query = query.where(
            or_(
                func.lower(Agent.name).like(pattern),
                func.lower(Agent.phone).like(pattern),
                func.lower(Agent.email).like(pattern),
                func.lower(Agent.address).like(pattern),
            )
        )

    query = query.order_by(Agent.name).offset(skip).limit(limit)
    return list(db.scalars(query).all())


def _validate_agent_uniqueness(
    db: Session,
    *,
    email: str | None = None,
    phone: str | None = None,
    agent_id: int | None = None,
) -> None:
    """Raise 409 if email or phone is already taken by another agent."""
    if email is not None:
        email_query = select(Agent).where(
            func.lower(Agent.email) == email.lower()
        )
        if agent_id is not None:
            email_query = email_query.where(Agent.id != agent_id)
        if db.scalar(email_query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Agent with this email already exists",
            )

    if phone is not None:
        phone_query = select(Agent).where(Agent.phone == phone)
        if agent_id is not None:
            phone_query = phone_query.where(Agent.id != agent_id)
        if db.scalar(phone_query) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Agent with this phone number already exists",
            )


def _commit_agent_changes(db: Session) -> None:
    """Commit the session, rolling back and raising on DB errors."""
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        logger.error("Agent integrity error on commit", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Agent data conflicts with an existing database record",
        ) from exc
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error("Agent database error on commit", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Unable to save agent data",
        ) from exc


def create_agent(db: Session, payload: AgentCreate) -> Agent:
    agent_data = payload.model_dump()

    _validate_agent_uniqueness(
        db,
        email=agent_data.get("email"),
        phone=agent_data.get("phone"),
    )

    agent = Agent(**agent_data)
    db.add(agent)
    _commit_agent_changes(db)
    db.refresh(agent)
    return agent


def update_agent(
    db: Session,
    agent: Agent,
    payload: AgentUpdate,
) -> Agent:
    update_data = payload.model_dump(exclude_unset=True)

    _validate_agent_uniqueness(
        db,
        email=update_data.get("email"),
        phone=update_data.get("phone"),
        agent_id=agent.id,
    )

    for field, value in update_data.items():
        setattr(agent, field, value)

    db.add(agent)
    _commit_agent_changes(db)
    db.refresh(agent)
    return agent


def deactivate_agent(db: Session, agent: Agent) -> Agent:
    """Soft-delete an agent by setting is_active = False."""
    if not agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is already inactive",
        )

    agent.is_active = False
    db.add(agent)
    _commit_agent_changes(db)
    db.refresh(agent)
    return agent


def reactivate_agent(db: Session, agent: Agent) -> Agent:
    """Restore a previously deactivated agent."""
    if agent.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent is already active",
        )

    agent.is_active = True
    db.add(agent)
    _commit_agent_changes(db)
    db.refresh(agent)
    return agent


def get_agent_stats(
    db: Session,
    agent_id: int,
    *,
    from_date: date | None = None,
    to_date: date | None = None,
) -> AgentStatsResponse:
    """Calculate patient referrals, billings, and earned commission for an agent."""
    agent = get_agent_or_404(db, agent_id)

    total_patients = (
        db.scalar(
            select(func.count(Patient.id)).where(
                Patient.agent_id == agent_id
            )
        )
        or 0
    )

    query = (
        select(Bill, Patient)
        .join(Patient, Bill.patient_id == Patient.id)
        .where(
            Patient.agent_id == agent_id,
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
        Decimal(str(agent.commission_percent))
        if agent.commission_percent is not None
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

    return AgentStatsResponse(
        agent_id=agent.id,
        agent_name=agent.name,
        commission_percent=commission_percent,
        total_patients=total_patients,
        total_bills=len(results),
        total_billed_amount=total_billed.quantize(Decimal("0.01")),
        total_paid_amount=total_paid.quantize(Decimal("0.01")),
        total_commission_earned=total_commission.quantize(Decimal("0.01")),
        recent_bills=recent_bills,
    )
