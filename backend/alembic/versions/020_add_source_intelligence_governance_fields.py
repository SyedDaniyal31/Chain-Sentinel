"""Add M4.2 source intelligence governance fields to scan_results

Revision ID: 020
Revises: 019
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "020"
down_revision: Union[str, None] = "019"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("governance_ownership_renounced", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("governance_source_confidence", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "governance_source_confidence")
    op.drop_column("scan_results", "governance_ownership_renounced")
