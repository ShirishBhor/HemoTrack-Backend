"""add expenses and refunds tables

Revision ID: 006_accounts_and_refunds
Revises: 005_payment_records
Create Date: 2026-10-11 20:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "006_accounts_and_refunds"
down_revision: Union[str, None] = "005_payment_records"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create expenses table
    op.create_table(
        "expenses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("voucher_number", sa.String(length=50), nullable=False),
        sa.Column(
            "category",
            sa.Enum(
                "REAGENTS_KITS",
                "LAB_CONSUMABLES",
                "EQUIPMENT_MAINTENANCE",
                "UTILITIES",
                "OFFICE_SUPPLIES",
                "SALARY_WAGES",
                "RENT",
                "WASTE_MANAGEMENT",
                "OTHER",
                name="expense_category",
            ),
            nullable=False,
            server_default="OTHER",
        ),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "payment_mode",
            sa.Enum("CASH", "UPI", "CARD", "NET_BANKING", "CHEQUE", name="expense_payment_mode"),
            nullable=False,
            server_default="CASH",
        ),
        sa.Column("expense_date", sa.Date(), nullable=False),
        sa.Column("payee", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("receipt_ref", sa.String(length=100), nullable=True),
        sa.Column("created_by_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_expenses_id"), "expenses", ["id"], unique=False)
    op.create_index(op.f("ix_expenses_voucher_number"), "expenses", ["voucher_number"], unique=True)
    op.create_index(op.f("ix_expenses_expense_date"), "expenses", ["expense_date"], unique=False)
    op.create_index(op.f("ix_expenses_created_by_id"), "expenses", ["created_by_id"], unique=False)

    # 2. Create refunds table
    op.create_table(
        "refunds",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("refund_number", sa.String(length=50), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "refund_mode",
            sa.Enum("CASH", "UPI", "ORIGINAL_PAYMENT_MODE", "BANK_TRANSFER", name="refund_mode"),
            nullable=False,
            server_default="CASH",
        ),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("transaction_ref", sa.String(length=100), nullable=True),
        sa.Column("processed_by_id", sa.Integer(), nullable=False),
        sa.Column("refund_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["processed_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_refunds_id"), "refunds", ["id"], unique=False)
    op.create_index(op.f("ix_refunds_refund_number"), "refunds", ["refund_number"], unique=True)
    op.create_index(op.f("ix_refunds_bill_id"), "refunds", ["bill_id"], unique=False)
    op.create_index(op.f("ix_refunds_refund_date"), "refunds", ["refund_date"], unique=False)
    op.create_index(op.f("ix_refunds_processed_by_id"), "refunds", ["processed_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refunds_processed_by_id"), table_name="refunds")
    op.drop_index(op.f("ix_refunds_refund_date"), table_name="refunds")
    op.drop_index(op.f("ix_refunds_bill_id"), table_name="refunds")
    op.drop_index(op.f("ix_refunds_refund_number"), table_name="refunds")
    op.drop_index(op.f("ix_refunds_id"), table_name="refunds")
    op.drop_table("refunds")

    op.drop_index(op.f("ix_expenses_created_by_id"), table_name="expenses")
    op.drop_index(op.f("ix_expenses_expense_date"), table_name="expenses")
    op.drop_index(op.f("ix_expenses_voucher_number"), table_name="expenses")
    op.drop_index(op.f("ix_expenses_id"), table_name="expenses")
    op.drop_table("expenses")
