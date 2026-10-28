"""create test categories table

Revision ID: 699f6683ca7b
Revises: 007_migrate_billing_fk
Create Date: 2026-10-22 12:28:15.319906

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '012_test_categories'
down_revision: Union[str, None] = '011_migrate_billing_fk'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_table(
        "test_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            server_default=sa.text("1"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_index(
        "ix_test_categories_id",
        "test_categories",
        ["id"],
        unique=False,
    )
    op.create_index(
        "ix_test_categories_name",
        "test_categories",
        ["name"],
        unique=True,
    )
    op.create_index(
        "ix_test_categories_code",
        "test_categories",
        ["code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_test_categories_code",
        table_name="test_categories",
    )
    op.drop_index(
        "ix_test_categories_name",
        table_name="test_categories",
    )
    op.drop_index(
        "ix_test_categories_id",
        table_name="test_categories",
    )
    op.drop_table("test_categories")

