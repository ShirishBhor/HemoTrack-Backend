"""add category_id to test_cases

Revision ID: a1b2c3d4e5f6
Revises: 699f6683ca7b
Create Date: 2026-10-22 14:37:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, None] = "699f6683ca7b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add category_id FK column to test_cases.
    # nullable=True so existing test cases are not broken;
    # they simply have no category until one is assigned.
    op.add_column(
        "test_cases",
        sa.Column(
            "category_id",
            sa.Integer(),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_test_cases_category_id",   # constraint name
        "test_cases",                  # source table
        "test_categories",             # referent table
        ["category_id"],               # local columns
        ["id"],                        # remote columns
        ondelete="SET NULL",
    )

    op.create_index(
        "ix_test_cases_category_id",
        "test_cases",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_test_cases_category_id",
        table_name="test_cases",
    )

    op.drop_constraint(
        "fk_test_cases_category_id",
        "test_cases",
        type_="foreignkey",
    )

    op.drop_column("test_cases", "category_id")
