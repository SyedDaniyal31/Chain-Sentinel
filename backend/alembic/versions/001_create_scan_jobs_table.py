"""Create scan_jobs table

Revision ID: 001
Revises:
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_type", sa.String(length=32), nullable=False),
        sa.Column("target_address", sa.String(length=42), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("risk_score", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_scan_jobs_target_address"), "scan_jobs", ["target_address"])
    op.create_index(op.f("ix_scan_jobs_status"), "scan_jobs", ["status"])


def downgrade() -> None:
    op.drop_index(op.f("ix_scan_jobs_status"), table_name="scan_jobs")
    op.drop_index(op.f("ix_scan_jobs_target_address"), table_name="scan_jobs")
    op.drop_table("scan_jobs")
