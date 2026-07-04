"""Add contract capability fields to scan_results

Revision ID: 010
Revises: 009
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("mint_capability", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("pause_capability", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("blacklist_capability", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("ownership_capability", sa.Boolean(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "ownership_capability")
    op.drop_column("scan_results", "blacklist_capability")
    op.drop_column("scan_results", "pause_capability")
    op.drop_column("scan_results", "mint_capability")
