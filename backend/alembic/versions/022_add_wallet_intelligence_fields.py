"""Add M5.2 wallet intelligence fields to scan_results

Revision ID: 022
Revises: 021
Create Date: 2026-06-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "022"
down_revision: Union[str, None] = "021"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("scan_results", sa.Column("wallet_creator", sa.String(length=42), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_deployer", sa.String(length=42), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_owner", sa.String(length=42), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_treasury", sa.String(length=42), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_funding_source", sa.String(length=16), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_funding_wallet", sa.String(length=42), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_is_fresh_deployer", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_reputation_known_scam", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_reputation_phishing", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_reputation_sanctioned", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_reputation_exploit_related", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_reputation_confidence", sa.String(length=16), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_lp_owner_is_creator", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_creator_owns_majority", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_exchange_funded_deployer", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_tornado_funded_deployer", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_treasury_is_multisig", sa.Boolean(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_risk_score", sa.Integer(), nullable=True))
    op.add_column("scan_results", sa.Column("wallet_relationship_graph", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("scan_results", "wallet_relationship_graph")
    op.drop_column("scan_results", "wallet_risk_score")
    op.drop_column("scan_results", "wallet_treasury_is_multisig")
    op.drop_column("scan_results", "wallet_tornado_funded_deployer")
    op.drop_column("scan_results", "wallet_exchange_funded_deployer")
    op.drop_column("scan_results", "wallet_creator_owns_majority")
    op.drop_column("scan_results", "wallet_lp_owner_is_creator")
    op.drop_column("scan_results", "wallet_reputation_confidence")
    op.drop_column("scan_results", "wallet_reputation_exploit_related")
    op.drop_column("scan_results", "wallet_reputation_sanctioned")
    op.drop_column("scan_results", "wallet_reputation_phishing")
    op.drop_column("scan_results", "wallet_reputation_known_scam")
    op.drop_column("scan_results", "wallet_is_fresh_deployer")
    op.drop_column("scan_results", "wallet_funding_wallet")
    op.drop_column("scan_results", "wallet_funding_source")
    op.drop_column("scan_results", "wallet_treasury")
    op.drop_column("scan_results", "wallet_owner")
    op.drop_column("scan_results", "wallet_deployer")
    op.drop_column("scan_results", "wallet_creator")
