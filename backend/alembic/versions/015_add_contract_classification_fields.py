"""Add contract classification fields to scan_results

Revision ID: 015
Revises: 014
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "015"
down_revision: Union[str, None] = "014"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("contract_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("proxy_type", sa.String(length=50), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("is_verified", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "is_verified")
    op.drop_column("scan_results", "proxy_type")
    op.drop_column("scan_results", "contract_type")
