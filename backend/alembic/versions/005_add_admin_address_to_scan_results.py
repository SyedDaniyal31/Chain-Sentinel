"""Add EIP-1967 admin field to scan_results

Revision ID: 005
Revises: 004
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("admin_address", sa.String(length=42), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "admin_address")
