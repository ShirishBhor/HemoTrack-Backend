"""
Author: Nikhil Yuvraj Mole
Date: 2026-10-26

Description:
SQLAlchemy model for Agent (field agent / marketing representative) entities.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
    )

    # India-only mobile number.
    # Application/schema validation ensures exactly 10 digits.
    phone: Mapped[str | None] = mapped_column(
        String(10),
        nullable=True,
        unique=True,
        index=True,
    )

    # Email is normalized to lowercase by the Pydantic schema.
    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        unique=True,
        index=True,
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    # Commission percentage paid to the agent (0.00 – 100.00).
    commission_percent: Mapped[float | None] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    patients = relationship(
        "Patient",
        back_populates="agent",
        foreign_keys="Patient.agent_id",
    )
