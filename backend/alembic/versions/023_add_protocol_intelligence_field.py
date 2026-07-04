"""Add M6.0 protocol intelligence JSONB field to scan_results

Revision ID: 023
Revises: 022
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "023"
down_revision: Union[str, None] = "022"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("protocol_intelligence", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "protocol_intelligence")
