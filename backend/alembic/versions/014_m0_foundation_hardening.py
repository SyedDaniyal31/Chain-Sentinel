"""M0 foundation hardening — chain context and analyzer metadata columns

Revision ID: 014
Revises: 013
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scan_jobs", sa.Column("chain_id", sa.Integer(), nullable=True))
    op.add_column("scan_jobs", sa.Column("block_number", sa.BigInteger(), nullable=True))
    op.add_column("scan_jobs", sa.Column("rpc_endpoint", sa.String(length=255), nullable=True))
    op.create_index("ix_scan_jobs_chain_id", "scan_jobs", ["chain_id"], unique=False)

    op.add_column("scan_results", sa.Column("detection_method", sa.String(length=50), nullable=True))
    op.add_column(
        "scan_results",
        sa.Column("analyzer_version", sa.String(length=50), nullable=True),
    )

    op.execute(
        """
        UPDATE scan_jobs sj
        SET chain_id = sr.chain_id,
            block_number = sr.latest_block
        FROM scan_results sr
        WHERE sr.scan_job_id = sj.id
          AND sj.chain_id IS NULL
        """
    )

    op.execute(
        """
        UPDATE scan_results
        SET analyzer_version = '1.1.0'
        WHERE analyzer_version IS NULL
        """
    )


def downgrade() -> None:
    op.drop_column("scan_results", "analyzer_version")
    op.drop_column("scan_results", "detection_method")
    op.drop_index("ix_scan_jobs_chain_id", table_name="scan_jobs")
    op.drop_column("scan_jobs", "rpc_endpoint")
    op.drop_column("scan_jobs", "block_number")
    op.drop_column("scan_jobs", "chain_id")
