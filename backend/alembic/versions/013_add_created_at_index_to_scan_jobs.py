"""Add created_at index to scan_jobs for history sorting

Revision ID: 013
Revises: 012
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_scan_jobs_created_at", "scan_jobs", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scan_jobs_created_at", table_name="scan_jobs")
