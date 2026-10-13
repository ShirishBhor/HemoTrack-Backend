"""add options calculated critical fields and reference ranges

Revision ID: b7a89e12c345
Revises: 90ce07b6cd74
Create Date: 2026-10-13 10:51:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b7a89e12c345'
down_revision: Union[str, None] = '90ce07b6cd74'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new clinical columns to test_parameters
    op.add_column('test_parameters', sa.Column('options', sa.Text(), nullable=True))
    op.add_column('test_parameters', sa.Column('is_calculated', sa.Boolean(), server_default='0', nullable=False))
    op.add_column('test_parameters', sa.Column('formula', sa.String(length=255), nullable=True))
    op.add_column('test_parameters', sa.Column('critical_low', sa.String(length=100), nullable=True))
    op.add_column('test_parameters', sa.Column('critical_high', sa.String(length=100), nullable=True))
    op.add_column('test_parameters', sa.Column('critical_action', sa.Text(), nullable=True))

    # Create parameter_reference_ranges table
    op.create_table(
        'parameter_reference_ranges',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parameter_id', sa.Integer(), nullable=False),
        sa.Column('gender', sa.String(length=20), server_default='all', nullable=False),
        sa.Column('min_age_days', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_age_days', sa.Integer(), server_default='54750', nullable=False),
        sa.Column('age_group_label', sa.String(length=100), nullable=True),
        sa.Column('min_value', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('max_value', sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column('normal_range_text', sa.String(length=255), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default='1', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['parameter_id'], ['test_parameters.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_parameter_reference_ranges_id'), 'parameter_reference_ranges', ['id'], unique=False)
    op.create_index(op.f('ix_parameter_reference_ranges_parameter_id'), 'parameter_reference_ranges', ['parameter_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_parameter_reference_ranges_parameter_id'), table_name='parameter_reference_ranges')
    op.drop_index(op.f('ix_parameter_reference_ranges_id'), table_name='parameter_reference_ranges')
    op.drop_table('parameter_reference_ranges')

    op.drop_column('test_parameters', 'critical_action')
    op.drop_column('test_parameters', 'critical_high')
    op.drop_column('test_parameters', 'critical_low')
    op.drop_column('test_parameters', 'formula')
    op.drop_column('test_parameters', 'is_calculated')
    op.drop_column('test_parameters', 'options')
