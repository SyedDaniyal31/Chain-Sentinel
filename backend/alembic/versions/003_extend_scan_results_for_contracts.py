"""Extend scan_results for contract analyzer output

Revision ID: 003
Revises: 002
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "scan_results",
        "wallet_balance_wei",
        existing_type=sa.BigInteger(),
        nullable=True,
    )
    op.add_column(
        "scan_results",
        sa.Column("is_contract", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("bytecode_size", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "bytecode_size")
    op.drop_column("scan_results", "is_contract")
    op.alter_column(
        "scan_results",
        "wallet_balance_wei",
        existing_type=sa.BigInteger(),
        nullable=False,
    )
