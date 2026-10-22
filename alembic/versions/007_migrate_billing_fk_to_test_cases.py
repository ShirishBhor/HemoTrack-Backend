"""migrate bill_items FK from test_master to test_cases, drop test_master and test_categories

Revision ID: 007_migrate_billing_fk_to_test_cases
Revises: 006_expenses_refunds
Create Date: 2026-10-22

Summary:
  - Drop the bill_items.test_id FK that pointed to test_master.id
  - Add a new bill_items.test_id FK pointing to test_cases.id (ON DELETE SET NULL)
  - Drop the now-unused test_master table
  - Drop the now-unused test_categories table
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007_migrate_billing_fk_to_test_cases"
down_revision: Union[str, Sequence[str], None] = ("b7a89e12c345", "006_accounts_and_refunds")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # 1. Drop the old FK constraint from bill_items → test_master if present
    bill_items_fks = [fk["name"] for fk in insp.get_foreign_keys("bill_items")]
    if "bill_items_ibfk_2" in bill_items_fks:
        op.drop_constraint("bill_items_ibfk_2", "bill_items", type_="foreignkey")

    # 2. Add the new FK constraint: bill_items.test_id → test_cases.id if not present
    if "fk_bill_items_test_cases" not in bill_items_fks:
        op.create_foreign_key(
            "fk_bill_items_test_cases",
            "bill_items",
            "test_cases",
            ["test_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # 3. Clean up test_master if exists
    tables = insp.get_table_names()
    if "test_master" in tables:
        tm_fks = [fk["name"] for fk in insp.get_foreign_keys("test_master")]
        if "test_master_ibfk_1" in tm_fks:
            op.drop_constraint("test_master_ibfk_1", "test_master", type_="foreignkey")

        tm_indexes = [idx["name"] for idx in insp.get_indexes("test_master")]
        for idx_name in [
            "ix_test_master_test_code",
            "ix_test_master_name",
            "ix_test_master_category_id",
            "ix_test_master_id",
        ]:
            if idx_name in tm_indexes:
                op.drop_index(idx_name, table_name="test_master")

        op.drop_table("test_master")

    # 4. Drop test_categories if exists
    if "test_categories" in tables:
        tc_indexes = [idx["name"] for idx in insp.get_indexes("test_categories")]
        for idx_name in ["ix_test_categories_name", "ix_test_categories_id"]:
            if idx_name in tc_indexes:
                op.drop_index(idx_name, table_name="test_categories")

        op.drop_table("test_categories")


def downgrade() -> None:
    # Restore test_categories
    op.create_table(
        "test_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_categories_id", "test_categories", ["id"], unique=False)
    op.create_index("ix_test_categories_name", "test_categories", ["name"], unique=True)

    # Restore test_master
    op.create_table(
        "test_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=True),
        sa.Column("test_code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("sample_type", sa.String(length=100), nullable=True),
        sa.Column("turnaround_time_hours", sa.Integer(), nullable=False, server_default="24"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["test_categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_master_id", "test_master", ["id"], unique=False)
    op.create_index("ix_test_master_category_id", "test_master", ["category_id"], unique=False)
    op.create_index("ix_test_master_name", "test_master", ["name"], unique=False)
    op.create_index("ix_test_master_test_code", "test_master", ["test_code"], unique=True)

    # Restore original FK: bill_items → test_master
    op.drop_constraint("fk_bill_items_test_cases", "bill_items", type_="foreignkey")
    op.create_foreign_key(
        "bill_items_ibfk_2",
        "bill_items",
        "test_master",
        ["test_id"],
        ["id"],
        ondelete="SET NULL",
    )
