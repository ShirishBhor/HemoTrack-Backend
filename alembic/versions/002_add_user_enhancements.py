"""add user enhancements

Revision ID: 002_user_enhancements
Revises: 001_initial
Create Date: 2026-10-08 17:48:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002_user_enhancements"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("employee_code", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_users_employee_code"), "users", ["employee_code"], unique=True)

    op.add_column("users", sa.Column("department", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_users_department"), "users", ["department"], unique=False)

    op.add_column("users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))

    op.add_column("users", sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default=sa.text("0")))

    op.add_column("users", sa.Column("is_locked", sa.Boolean(), nullable=False, server_default=sa.text("0")))

    op.add_column("users", sa.Column("profile_picture_url", sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "profile_picture_url")
    op.drop_column("users", "is_locked")
    op.drop_column("users", "failed_login_attempts")
    op.drop_column("users", "last_login_at")

    op.drop_index(op.f("ix_users_department"), table_name="users")
    op.drop_column("users", "department")

    op.drop_index(op.f("ix_users_employee_code"), table_name="users")
    op.drop_column("users", "employee_code")
