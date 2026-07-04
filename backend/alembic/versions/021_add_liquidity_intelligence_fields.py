"""Add M5.1 liquidity intelligence fields to scan_results

Revision ID: 021
Revises: 020
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "021"
down_revision: Union[str, None] = "020"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("liquidity_has_liquidity", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_usd", sa.Numeric(precision=18, scale=2), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_primary_dex", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_pair_address", sa.String(length=42), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_lp_owner", sa.String(length=42), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_locked", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_lock_percentage", sa.Numeric(precision=5, scale=2), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_lock_expiry", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("liquidity_top_pools", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "liquidity_top_pools")
    op.drop_column("scan_results", "liquidity_lock_expiry")
    op.drop_column("scan_results", "liquidity_lock_percentage")
    op.drop_column("scan_results", "liquidity_locked")
    op.drop_column("scan_results", "liquidity_lp_owner")
    op.drop_column("scan_results", "liquidity_pair_address")
    op.drop_column("scan_results", "liquidity_primary_dex")
    op.drop_column("scan_results", "liquidity_usd")
    op.drop_column("scan_results", "liquidity_has_liquidity")
