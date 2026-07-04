"""Add M4 honeypot intelligence fields to scan_results

Revision ID: 019
Revises: 018
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "019"
down_revision: Union[str, None] = "018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("honeypot_score", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_risk", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_finding_count", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_is_suspected", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_is_confirmed", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_simulation_status", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_findings", sa.JSON(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("honeypot_simulation", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "honeypot_simulation")
    op.drop_column("scan_results", "honeypot_findings")
    op.drop_column("scan_results", "honeypot_simulation_status")
    op.drop_column("scan_results", "honeypot_is_confirmed")
    op.drop_column("scan_results", "honeypot_is_suspected")
    op.drop_column("scan_results", "honeypot_finding_count")
    op.drop_column("scan_results", "honeypot_risk")
    op.drop_column("scan_results", "honeypot_score")
