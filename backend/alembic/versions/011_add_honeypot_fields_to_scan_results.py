"""Add honeypot / trading-restriction fields to scan_results

Revision ID: 011
Revises: 010
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "011"
down_revision: Union[str, None] = "010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("trading_enabled_control", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("whitelist_control", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("blacklist_sell_blocking", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("transfer_tax_control", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "transfer_tax_control")
    op.drop_column("scan_results", "blacklist_sell_blocking")
    op.drop_column("scan_results", "whitelist_control")
    op.drop_column("scan_results", "trading_enabled_control")
