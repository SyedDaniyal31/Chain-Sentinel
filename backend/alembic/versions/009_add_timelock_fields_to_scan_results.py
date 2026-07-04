"""Add timelock governance fields to scan_results

Revision ID: 009
Revises: 008
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("is_timelock", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("min_delay", sa.BigInteger(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "min_delay")
    op.drop_column("scan_results", "is_timelock")
