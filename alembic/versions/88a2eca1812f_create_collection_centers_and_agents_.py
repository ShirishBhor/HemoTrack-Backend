"""create_collection_centers_and_agents_tables

Revision ID: 88a2eca1812f
Revises: a1b2c3d4e5f6
Create Date: 2026-10-26 09:47:45.339353

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '88a2eca1812f'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create collection_centers table
    op.create_table(
        "collection_centers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("contact_person", sa.String(length=255), nullable=True),
        sa.Column("commission_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index(op.f("ix_collection_centers_id"), "collection_centers", ["id"], unique=False)
    op.create_index(op.f("ix_collection_centers_name"), "collection_centers", ["name"], unique=False)
    op.create_index(op.f("ix_collection_centers_phone"), "collection_centers", ["phone"], unique=True)
    op.create_index(op.f("ix_collection_centers_email"), "collection_centers", ["email"], unique=True)

    # 2. Create agents table
    op.create_table(
        "agents",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=10), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("commission_percent", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("phone"),
    )
    op.create_index(op.f("ix_agents_id"), "agents", ["id"], unique=False)
    op.create_index(op.f("ix_agents_name"), "agents", ["name"], unique=False)
    op.create_index(op.f("ix_agents_phone"), "agents", ["phone"], unique=True)
    op.create_index(op.f("ix_agents_email"), "agents", ["email"], unique=True)

    # 3. Add collection_center_id and agent_id to patients table
    op.add_column("patients", sa.Column("collection_center_id", sa.Integer(), nullable=True))
    op.add_column("patients", sa.Column("agent_id", sa.Integer(), nullable=True))

    op.create_foreign_key(
        "fk_patients_collection_center_id",
        "patients",
        "collection_centers",
        ["collection_center_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_foreign_key(
        "fk_patients_agent_id",
        "patients",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_index(op.f("ix_patients_collection_center_id"), "patients", ["collection_center_id"], unique=False)
    op.create_index(op.f("ix_patients_agent_id"), "patients", ["agent_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_patients_agent_id"), table_name="patients")
    op.drop_index(op.f("ix_patients_collection_center_id"), table_name="patients")
    op.drop_constraint("fk_patients_agent_id", "patients", type_="foreignkey")
    op.drop_constraint("fk_patients_collection_center_id", "patients", type_="foreignkey")
    op.drop_column("patients", "agent_id")
    op.drop_column("patients", "collection_center_id")

    op.drop_index(op.f("ix_agents_email"), table_name="agents")
    op.drop_index(op.f("ix_agents_phone"), table_name="agents")
    op.drop_index(op.f("ix_agents_name"), table_name="agents")
    op.drop_index(op.f("ix_agents_id"), table_name="agents")
    op.drop_table("agents")

    op.drop_index(op.f("ix_collection_centers_email"), table_name="collection_centers")
    op.drop_index(op.f("ix_collection_centers_phone"), table_name="collection_centers")
    op.drop_index(op.f("ix_collection_centers_name"), table_name="collection_centers")
    op.drop_index(op.f("ix_collection_centers_id"), table_name="collection_centers")
    op.drop_table("collection_centers")

