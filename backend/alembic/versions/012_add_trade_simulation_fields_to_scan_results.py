"""Add trade simulation fields to scan_results

Revision ID: 012
Revises: 011
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "012"
down_revision: Union[str, None] = "011"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("trade_simulated", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("can_buy", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("can_sell", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("buy_tax_bps", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("sell_tax_bps", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "sell_tax_bps")
    op.drop_column("scan_results", "buy_tax_bps")
    op.drop_column("scan_results", "can_sell")
    op.drop_column("scan_results", "can_buy")
    op.drop_column("scan_results", "trade_simulated")
