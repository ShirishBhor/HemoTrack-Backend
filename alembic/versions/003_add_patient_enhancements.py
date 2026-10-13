"""add patient enhancements

Revision ID: 003_patient_enhancements
Revises: 002_user_enhancements
Create Date: 2026-10-08 18:14:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003_patient_enhancements"
down_revision: Union[str, None] = "002_user_enhancements"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add nullable uhid column
    op.add_column("patients", sa.Column("uhid", sa.String(length=50), nullable=True))
    
    # 2. Populate uhid for any pre-existing records safely
    op.execute("UPDATE patients SET uhid = CONCAT('HT-', YEAR(NOW()), '-', LPAD(id, 5, '0')) WHERE uhid IS NULL")

    # 3. Make uhid NOT NULL and create unique index
    op.alter_column("patients", "uhid", existing_type=sa.String(length=50), nullable=False)
    op.create_index(op.f("ix_patients_uhid"), "patients", ["uhid"], unique=True)

    # 4. Add remaining columns and indexes
    op.add_column("patients", sa.Column("dob", sa.Date(), nullable=True))

    op.add_column(
        "patients",
        sa.Column(
            "blood_group",
            sa.Enum(
                "A+",
                "A-",
                "B+",
                "B-",
                "AB+",
                "AB-",
                "O+",
                "O-",
                "UNKNOWN",
                name="blood_group",
            ),
            nullable=False,
            server_default="UNKNOWN",
        ),
    )

    op.add_column("patients", sa.Column("national_id", sa.String(length=50), nullable=True))
    op.create_index(op.f("ix_patients_national_id"), "patients", ["national_id"], unique=False)

    op.add_column(
        "patients",
        sa.Column(
            "marital_status",
            sa.Enum(
                "SINGLE",
                "MARRIED",
                "DIVORCED",
                "WIDOWED",
                "OTHER",
                name="marital_status",
            ),
            nullable=True,
        ),
    )

    op.add_column("patients", sa.Column("guardian_name", sa.String(length=255), nullable=True))
    op.add_column("patients", sa.Column("emergency_contact_name", sa.String(length=255), nullable=True))
    op.add_column("patients", sa.Column("emergency_contact_phone", sa.String(length=30), nullable=True))
    op.add_column("patients", sa.Column("relationship_to_patient", sa.String(length=50), nullable=True))

    op.add_column("patients", sa.Column("sample_barcode", sa.String(length=100), nullable=True))
    op.create_index(op.f("ix_patients_sample_barcode"), "patients", ["sample_barcode"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_patients_sample_barcode"), table_name="patients")
    op.drop_column("patients", "sample_barcode")

    op.drop_column("patients", "relationship_to_patient")
    op.drop_column("patients", "emergency_contact_phone")
    op.drop_column("patients", "emergency_contact_name")
    op.drop_column("patients", "guardian_name")
    op.drop_column("patients", "marital_status")

    op.drop_index(op.f("ix_patients_national_id"), table_name="patients")
    op.drop_column("patients", "national_id")

    op.drop_column("patients", "blood_group")
    op.drop_column("patients", "dob")

    op.drop_index(op.f("ix_patients_uhid"), table_name="patients")
    op.drop_column("patients", "uhid")
