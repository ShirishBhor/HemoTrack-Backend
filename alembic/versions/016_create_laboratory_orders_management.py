"""
Alembic Migration: 016_create_laboratory_orders_management
Creates:
  - lab_orders
  - lab_order_items
  - lab_samples
  - lab_results
  - lab_reports
"""

from alembic import op
import sqlalchemy as sa


revision = "016_create_laboratory_orders_management"
down_revision = "015_rename_to_departments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. lab_orders
    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_number", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("collection_center_id", sa.Integer(), sa.ForeignKey("collection_centers.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("priority", sa.String(length=20), nullable=False, server_default="ROUTINE"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
        sa.Column("order_date", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("clinical_notes", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("is_cancelled", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 2. lab_order_items
    op.create_table(
        "lab_order_items",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("test_case_id", sa.Integer(), sa.ForeignKey("test_cases.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("price", sa.Numeric(precision=10, scale=2), nullable=False, server_default="0.00"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="ORDERED"),
        sa.Column("cancellation_reason", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 3. lab_samples
    op.create_table(
        "lab_samples",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("sample_number", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("barcode", sa.String(length=100), nullable=False, unique=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("sample_type", sa.String(length=100), nullable=False),
        sa.Column("container_type", sa.String(length=100), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING_COLLECTION"),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # 4. lab_results
    op.create_table(
        "lab_results",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("order_item_id", sa.Integer(), sa.ForeignKey("lab_order_items.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parameter_id", sa.Integer(), sa.ForeignKey("test_parameters.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("result_value", sa.String(length=255), nullable=False),
        sa.Column("numeric_value", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("unit", sa.String(length=100), nullable=True),
        sa.Column("reference_range", sa.String(length=255), nullable=True),
        sa.Column("abnormality_flag", sa.String(length=20), nullable=False, server_default="NORMAL"),
        sa.Column("status", sa.String(length=30), nullable=False, server_default="DRAFT"),
        sa.Column("comments", sa.Text(), nullable=True),
        sa.Column("entered_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("entered_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("verified_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
        sa.UniqueConstraint("order_item_id", "parameter_id", name="uq_lab_results_item_parameter"),
    )

    # 5. lab_reports
    op.create_table(
        "lab_reports",
        sa.Column("id", sa.Integer(), primary_key=True, index=True),
        sa.Column("report_number", sa.String(length=50), nullable=False, unique=True, index=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("lab_orders.id", ondelete="CASCADE"), nullable=False, unique=True, index=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id", ondelete="RESTRICT"), nullable=False, index=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="GENERATED"),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("finalized_by_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("summary_notes", sa.Text(), nullable=True),
        sa.Column("report_data_snapshot", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now(), onupdate=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("lab_reports")
    op.drop_table("lab_results")
    op.drop_table("lab_samples")
    op.drop_table("lab_order_items")
    op.drop_table("lab_orders")
