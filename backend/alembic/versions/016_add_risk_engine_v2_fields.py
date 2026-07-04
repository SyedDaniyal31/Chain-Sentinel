"""Add Risk Engine V2 dimension fields to scan_results

Revision ID: 016
Revises: 015
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "016"
down_revision: Union[str, None] = "015"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("threat_level", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("centralization_level", sa.String(length=16), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("confidence_level", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "confidence_level")
    op.drop_column("scan_results", "centralization_level")
    op.drop_column("scan_results", "threat_level")
