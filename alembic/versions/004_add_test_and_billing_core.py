"""add test master and billing core

Revision ID: 004_billing_core
Revises: 003_patient_enhancements
Create Date: 2026-10-11 19:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004_billing_core"
down_revision: Union[str, None] = "003_patient_enhancements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create test_categories
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
    op.create_index(op.f("ix_test_categories_id"), "test_categories", ["id"], unique=False)
    op.create_index(op.f("ix_test_categories_name"), "test_categories", ["name"], unique=True)

    # 2. Create test_master
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
    op.create_index(op.f("ix_test_master_id"), "test_master", ["id"], unique=False)
    op.create_index(op.f("ix_test_master_category_id"), "test_master", ["category_id"], unique=False)
    op.create_index(op.f("ix_test_master_name"), "test_master", ["name"], unique=False)
    op.create_index(op.f("ix_test_master_test_code"), "test_master", ["test_code"], unique=True)

    # 3. Create bills
    op.create_table(
        "bills",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_number", sa.String(length=50), nullable=False),
        sa.Column("patient_id", sa.Integer(), nullable=False),
        sa.Column("doctor_id", sa.Integer(), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("UNPAID", "PARTIALLY_PAID", "PAID", "CANCELLED", name="bill_status"),
            nullable=False,
            server_default="UNPAID",
        ),
        sa.Column("subtotal", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column(
            "discount_type",
            sa.Enum("NONE", "FLAT", "PERCENTAGE", name="discount_type"),
            nullable=False,
            server_default="NONE",
        ),
        sa.Column("discount_value", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("discount_reason", sa.String(length=255), nullable=True),
        sa.Column("payable_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("paid_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("due_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("remarks", sa.Text(), nullable=True),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), nullable=True),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["cancelled_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["doctor_id"], ["doctors.id"]),
        sa.ForeignKeyConstraint(["patient_id"], ["patients.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bills_id"), "bills", ["id"], unique=False)
    op.create_index(op.f("ix_bills_bill_number"), "bills", ["bill_number"], unique=True)
    op.create_index(op.f("ix_bills_created_by_id"), "bills", ["created_by_id"], unique=False)
    op.create_index(op.f("ix_bills_doctor_id"), "bills", ["doctor_id"], unique=False)
    op.create_index(op.f("ix_bills_patient_id"), "bills", ["patient_id"], unique=False)

    # 4. Create bill_items
    op.create_table(
        "bill_items",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=True),
        sa.Column("test_name", sa.String(length=255), nullable=False),
        sa.Column("test_code", sa.String(length=50), nullable=False),
        sa.Column("unit_price", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("discount_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("line_total", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_id"], ["test_master.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_bill_items_id"), "bill_items", ["id"], unique=False)
    op.create_index(op.f("ix_bill_items_bill_id"), "bill_items", ["bill_id"], unique=False)
    op.create_index(op.f("ix_bill_items_test_id"), "bill_items", ["test_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_bill_items_test_id"), table_name="bill_items")
    op.drop_index(op.f("ix_bill_items_bill_id"), table_name="bill_items")
    op.drop_index(op.f("ix_bill_items_id"), table_name="bill_items")
    op.drop_table("bill_items")

    op.drop_index(op.f("ix_bills_patient_id"), table_name="bills")
    op.drop_index(op.f("ix_bills_doctor_id"), table_name="bills")
    op.drop_index(op.f("ix_bills_created_by_id"), table_name="bills")
    op.drop_index(op.f("ix_bills_bill_number"), table_name="bills")
    op.drop_index(op.f("ix_bills_id"), table_name="bills")
    op.drop_table("bills")

    op.drop_index(op.f("ix_test_master_test_code"), table_name="test_master")
    op.drop_index(op.f("ix_test_master_name"), table_name="test_master")
    op.drop_index(op.f("ix_test_master_category_id"), table_name="test_master")
    op.drop_index(op.f("ix_test_master_id"), table_name="test_master")
    op.drop_table("test_master")

    op.drop_index(op.f("ix_test_categories_name"), table_name="test_categories")
    op.drop_index(op.f("ix_test_categories_id"), table_name="test_categories")
    op.drop_table("test_categories")
