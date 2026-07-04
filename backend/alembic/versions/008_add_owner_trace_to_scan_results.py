"""Add ProxyAdmin owner trace fields to scan_results

Revision ID: 008
Revises: 007
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("owner_address", sa.String(length=42), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("owner_type", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "owner_type")
    op.drop_column("scan_results", "owner_address")
