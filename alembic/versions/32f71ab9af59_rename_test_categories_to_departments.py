"""rename_test_categories_to_departments

Revision ID: 32f71ab9af59
Revises: 88a2eca1812f
Create Date: 2026-10-28 17:37:57.171508

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '32f71ab9af59'
down_revision: Union[str, None] = '88a2eca1812f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Drop foreign keys and indexes on test_cases referencing test_categories
    if "test_cases" in tables:
        tc_fks = [fk["name"] for fk in insp.get_foreign_keys("test_cases")]
        for fk_name in tc_fks:
            if fk_name and ("category" in fk_name.lower()):
                op.drop_constraint(fk_name, "test_cases", type_="foreignkey")

        tc_indexes = [idx["name"] for idx in insp.get_indexes("test_cases")]
        if "ix_test_cases_category_id" in tc_indexes:
            op.drop_index("ix_test_cases_category_id", table_name="test_cases")

    # 2. Rename test_categories table to departments
    if "test_categories" in tables:
        # Drop old indexes before renaming
        cat_indexes = [idx["name"] for idx in insp.get_indexes("test_categories")]
        for idx_name in [
            "ix_test_categories_code",
            "ix_test_categories_name",
            "ix_test_categories_id",
        ]:
            if idx_name in cat_indexes:
                op.drop_index(idx_name, table_name="test_categories")

        op.rename_table("test_categories", "departments")

        # Create new indexes on departments
        op.create_index(
            "ix_departments_id",
            "departments",
            ["id"],
            unique=False,
        )
        op.create_index(
            "ix_departments_name",
            "departments",
            ["name"],
            unique=True,
        )
        op.create_index(
            "ix_departments_code",
            "departments",
            ["code"],
            unique=True,
        )

    # 3. Rename category_id column to department_id in test_cases
    if "test_cases" in tables:
        cols = [c["name"] for c in insp.get_columns("test_cases")]
        if "category_id" in cols and "department_id" not in cols:
            op.alter_column(
                "test_cases",
                "category_id",
                new_column_name="department_id",
                existing_type=sa.Integer(),
                nullable=True,
            )

        tc_indexes_after = [idx["name"] for idx in insp.get_indexes("test_cases")]
        if "ix_test_cases_department_id" not in tc_indexes_after:
            op.create_index(
                "ix_test_cases_department_id",
                "test_cases",
                ["department_id"],
                unique=False,
            )

        tc_fks_after = [fk["name"] for fk in insp.get_foreign_keys("test_cases")]
        if "fk_test_cases_department_id" not in tc_fks_after:
            op.create_foreign_key(
                "fk_test_cases_department_id",
                "test_cases",
                "departments",
                ["department_id"],
                ["id"],
                ondelete="SET NULL",
            )


def downgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    tables = insp.get_table_names()

    # 1. Drop foreign keys and index on test_cases.department_id
    if "test_cases" in tables:
        tc_fks = [fk["name"] for fk in insp.get_foreign_keys("test_cases")]
        if "fk_test_cases_department_id" in tc_fks:
            op.drop_constraint("fk_test_cases_department_id", "test_cases", type_="foreignkey")

        tc_indexes = [idx["name"] for idx in insp.get_indexes("test_cases")]
        if "ix_test_cases_department_id" in tc_indexes:
            op.drop_index("ix_test_cases_department_id", table_name="test_cases")

    # 2. Rename departments table back to test_categories
    if "departments" in tables:
        dept_indexes = [idx["name"] for idx in insp.get_indexes("departments")]
        for idx_name in [
            "ix_departments_code",
            "ix_departments_name",
            "ix_departments_id",
        ]:
            if idx_name in dept_indexes:
                op.drop_index(idx_name, table_name="departments")

        op.rename_table("departments", "test_categories")

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

    # 3. Rename department_id back to category_id in test_cases
    if "test_cases" in tables:
        cols = [c["name"] for c in insp.get_columns("test_cases")]
        if "department_id" in cols and "category_id" not in cols:
            op.alter_column(
                "test_cases",
                "department_id",
                new_column_name="category_id",
                existing_type=sa.Integer(),
                nullable=True,
            )

        tc_indexes_after = [idx["name"] for idx in insp.get_indexes("test_cases")]
        if "ix_test_cases_category_id" not in tc_indexes_after:
            op.create_index(
                "ix_test_cases_category_id",
                "test_cases",
                ["category_id"],
                unique=False,
            )

        tc_fks_after = [fk["name"] for fk in insp.get_foreign_keys("test_cases")]
        if "fk_test_cases_category_id" not in tc_fks_after:
            op.create_foreign_key(
                "fk_test_cases_category_id",
                "test_cases",
                "test_categories",
                ["category_id"],
                ["id"],
                ondelete="SET NULL",
            )
