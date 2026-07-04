"""Add EIP-1967 proxy fields to scan_results

Revision ID: 004
Revises: 003
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("is_upgradeable", sa.Boolean(), nullable=True),
    )
    op.add_column(
        "scan_results",
        sa.Column("implementation_address", sa.String(length=42), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "implementation_address")
    op.drop_column("scan_results", "is_upgradeable")
