"""create_packages_tables

Revision ID: 016_create_packages_tables
Revises: 015_rename_to_departments
Create Date: 2026-11-02 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '016_create_packages_tables'
down_revision: Union[str, None] = '015_rename_to_departments'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create packages table
    op.create_table(
        "packages",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), server_default="0.00", nullable=False),
        sa.Column("tat", sa.String(length=100), nullable=True),
        sa.Column("sample_requirements", sa.String(length=255), nullable=True),
        sa.Column("fasting_required", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("department_id", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.true(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["department_id"], ["departments.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_packages_id"), "packages", ["id"], unique=False)
    op.create_index(op.f("ix_packages_name"), "packages", ["name"], unique=False)
    op.create_index(op.f("ix_packages_code"), "packages", ["code"], unique=True)
    op.create_index(op.f("ix_packages_department_id"), "packages", ["department_id"], unique=False)

    # 2. Create package_test_cases junction table
    op.create_table(
        "package_test_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("package_id", sa.Integer(), nullable=False),
        sa.Column("test_case_id", sa.Integer(), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="1", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["package_id"], ["packages.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["test_case_id"], ["test_cases.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("package_id", "test_case_id", name="uq_package_test_case"),
    )
    op.create_index(op.f("ix_package_test_cases_id"), "package_test_cases", ["id"], unique=False)
    op.create_index(op.f("ix_package_test_cases_package_id"), "package_test_cases", ["package_id"], unique=False)
    op.create_index(op.f("ix_package_test_cases_test_case_id"), "package_test_cases", ["test_case_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_package_test_cases_test_case_id"), table_name="package_test_cases")
    op.drop_index(op.f("ix_package_test_cases_package_id"), table_name="package_test_cases")
    op.drop_index(op.f("ix_package_test_cases_id"), table_name="package_test_cases")
    op.drop_table("package_test_cases")

    op.drop_index(op.f("ix_packages_department_id"), table_name="packages")
    op.drop_index(op.f("ix_packages_code"), table_name="packages")
    op.drop_index(op.f("ix_packages_name"), table_name="packages")
    op.drop_index(op.f("ix_packages_id"), table_name="packages")
    op.drop_table("packages")

