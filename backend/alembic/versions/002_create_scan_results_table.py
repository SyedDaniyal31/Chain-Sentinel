"""Create scan_results table

Revision ID: 002
Revises: 001
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "scan_results",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scan_job_id", sa.Integer(), nullable=False),
        sa.Column("chain_id", sa.Integer(), nullable=False),
        sa.Column("latest_block", sa.BigInteger(), nullable=False),
        sa.Column("wallet_balance_wei", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["scan_job_id"], ["scan_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scan_job_id"),
    )
    op.create_index(op.f("ix_scan_results_scan_job_id"), "scan_results", ["scan_job_id"])


def downgrade() -> None:
    op.drop_index(op.f("ix_scan_results_scan_job_id"), table_name="scan_results")
    op.drop_table("scan_results")
