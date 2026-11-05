"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
API router for Agent management.

Available operations:
- GET    /agents                      — List all agents (paginated + search)
- POST   /agents                      — Create a new agent
- GET    /agents/{id}                 — Get an agent by ID
- PATCH  /agents/{id}                 — Update an agent
- PATCH  /agents/{id}/status          — Activate or deactivate an agent
"""

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, status

from app.core.deps import CurrentUser, DbSession, require_roles
from app.models.user import User, UserRole
from app.schemas.common import StatusUpdate
from app.schemas.agent import (
    AgentCreate,
    AgentListResponse,
    AgentRead,
    AgentStatsResponse,
    AgentUpdate,
)
from app.schemas.patient import PatientRead
from app.services import agent_service, patient_service


router = APIRouter(prefix="/agents", tags=["agents"])


# ============================================================
# PERMISSION GROUPS
# ============================================================

AgentWriteUser = Annotated[
    User,
    Depends(
        require_roles(
            UserRole.ADMIN,
            UserRole.LAB_MANAGER,
            UserRole.RECEPTIONIST,
        )
    ),
]

AgentManageUser = Annotated[
    User,
    Depends(require_roles(UserRole.ADMIN, UserRole.LAB_MANAGER)),
]


# ============================================================
# LIST AGENTS
# ============================================================

@router.get("", response_model=AgentListResponse)
def list_agents(
    db: DbSession,
    _: CurrentUser,
    skip: int = Query(
        default=0,
        ge=0,
        description="Number of records to skip",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=200,
        description="Maximum number of records to return",
    ),
    search: str | None = Query(
        default=None,
        max_length=255,
        description="Search by name, phone, email, or address",
    ),
    is_active: bool | None = Query(
        default=None,
        description="Filter by active status (true for active agents, false for inactive agents)",
    ),
):
    """
    List agents with pagination and optional search.

    Returns total count alongside items so clients can build
    pagination controls without a separate request.
    """
    total = agent_service.count_agents(
        db,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )
    items = agent_service.list_agents(
        db,
        skip=skip if isinstance(skip, int) else 0,
        limit=limit if isinstance(limit, int) else 50,
        search=search if isinstance(search, str) else None,
        is_active=is_active if isinstance(is_active, bool) else None,
    )
    return AgentListResponse(total=total, items=items)


# ============================================================
# CREATE AGENT
# ============================================================

@router.post("", response_model=AgentRead, status_code=status.HTTP_201_CREATED)
def create_agent(
    payload: AgentCreate,
    db: DbSession,
    _: AgentWriteUser,
):
    """
    Create a new agent.

    Only ADMIN, LAB_MANAGER, and RECEPTIONIST can create agents.
    """
    return agent_service.create_agent(db, payload)


# ============================================================
# GET AGENT BY ID
# ============================================================

@router.get("/{agent_id}", response_model=AgentRead)
def get_agent(
    db: DbSession,
    _: CurrentUser,
    agent_id: int = Path(..., gt=0, description="Agent ID"),
):
    """
    Get a single agent by ID.

    Any authenticated user can access this endpoint.
    """
    return agent_service.get_agent_or_404(db, agent_id)


# ============================================================
# UPDATE AGENT
# ============================================================

@router.patch("/{agent_id}", response_model=AgentRead)
def update_agent(
    payload: AgentUpdate,
    db: DbSession,
    _: AgentWriteUser,
    agent_id: int = Path(..., gt=0, description="Agent ID"),
):
    """
    Partially update an existing agent.

    Only ADMIN, LAB_MANAGER, and RECEPTIONIST can update agents.
    To change the active status use /status.
    """
    agent = agent_service.get_agent_or_404(db, agent_id)
    return agent_service.update_agent(db, agent, payload)


# ============================================================
# UPDATE AGENT STATUS
# ============================================================

@router.patch("/{agent_id}/status", response_model=AgentRead)
def update_agent_status(
    payload: StatusUpdate,
    db: DbSession,
    _: AgentManageUser,
    agent_id: int = Path(..., gt=0, description="Agent ID"),
):
    """
    Activate or deactivate an agent.

    Only ADMIN and LAB_MANAGER can change agent status.
    """
    agent = agent_service.get_agent_or_404(db, agent_id)
    return agent_service.update_agent_status(db, agent, payload.is_active)


# ============================================================
# GET PATIENTS FOR AGENT
# ============================================================

@router.get("/{agent_id}/patients", response_model=list[PatientRead])
def list_agent_patients(
    db: DbSession,
    _: CurrentUser,
    agent_id: int = Path(..., gt=0, description="Agent ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    search: str | None = Query(default=None, max_length=255),
):
    """
    Get all patients registered through a specific agent.
    """
    agent_service.get_agent_or_404(db, agent_id)
    return patient_service.list_patients(
        db,
        skip=skip,
        limit=limit,
        search=search,
        agent_id=agent_id,
    )


# ============================================================
# GET AGENT STATS & COMMISSIONS
# ============================================================

@router.get("/{agent_id}/stats", response_model=AgentStatsResponse)
def get_agent_stats(
    db: DbSession,
    _: CurrentUser,
    agent_id: int = Path(..., gt=0, description="Agent ID"),
    from_date: date | None = Query(default=None, description="Start date for referral billing stats"),
    to_date: date | None = Query(default=None, description="End date for referral billing stats"),
):
    """
    Get business metrics, referral patient count, total sales, and earned commission for an agent.
    """
    return agent_service.get_agent_stats(
        db,
        agent_id,
        from_date=from_date,
        to_date=to_date,
    )
