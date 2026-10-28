"""add unique test parameter code constraint

Revision ID: 90ce07b6cd74
Revises: 4d26fbb36aff
Create Date: 2026-10-09 09:45:51.657562

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '009_unique_param_code'
down_revision: Union[str, None] = '008_test_parameters'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    op.create_unique_constraint(
        "uq_test_parameters_test_case_code",
        "test_parameters",
        ["test_case_id", "code"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_test_parameters_test_case_code",
        "test_parameters",
        type_="unique",
    )