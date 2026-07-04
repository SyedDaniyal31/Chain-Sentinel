"""Add admin_type to scan_results

Revision ID: 007
Revises: 006
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_results",
        sa.Column("admin_type", sa.String(length=16), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("scan_results", "admin_type")
