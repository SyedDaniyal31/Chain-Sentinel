"""Add M2 governance intelligence fields to scan_results

Revision ID: 017
Revises: 016
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "017"
down_revision: Union[str, None] = "016"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("governance_type", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("upgrade_authority", sa.String(length=32), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("role_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("governance_roles", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("governance_ownership_address", sa.String(length=42), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "governance_ownership_address")
    op.drop_column("scan_results", "governance_roles")
    op.drop_column("scan_results", "role_count")
    op.drop_column("scan_results", "upgrade_authority")
    op.drop_column("scan_results", "governance_type")
