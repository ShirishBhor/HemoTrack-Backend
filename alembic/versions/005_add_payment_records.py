"""add payments table

Revision ID: 005_payment_records
Revises: 004_billing_core
Create Date: 2026-10-11 19:50:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005_payment_records"
down_revision: Union[str, None] = "004_billing_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("receipt_number", sa.String(length=50), nullable=False),
        sa.Column("bill_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=10, scale=2), nullable=False),
        sa.Column(
            "payment_mode",
            sa.Enum("CASH", "UPI", "CARD", "NET_BANKING", "CHEQUE", name="payment_mode"),
            nullable=False,
            server_default="CASH",
        ),
        sa.Column("transaction_ref", sa.String(length=100), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("received_by_id", sa.Integer(), nullable=False),
        sa.Column("payment_date", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["received_by_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_payments_id"), "payments", ["id"], unique=False)
    op.create_index(op.f("ix_payments_receipt_number"), "payments", ["receipt_number"], unique=True)
    op.create_index(op.f("ix_payments_bill_id"), "payments", ["bill_id"], unique=False)
    op.create_index(op.f("ix_payments_received_by_id"), "payments", ["received_by_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_received_by_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_bill_id"), table_name="payments")
    op.drop_index(op.f("ix_payments_receipt_number"), table_name="payments")
    op.drop_index(op.f("ix_payments_id"), table_name="payments")
    op.drop_table("payments")
