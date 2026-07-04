"""Wallet intelligence builders for M5.2."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.wallet.funding_classifier import (
    classify_funding_source,
    find_first_inbound_funding,
    is_fresh_wallet,
)
from app.blockchain.wallet.reputation_provider import WalletReputationResult
from app.blockchain.wallet.wallet_history_provider import ExplorerTransaction
from app.models.enums import (
    AdminType,
    ConfidenceLevel,
    FundingSourceType,
    UpgradeAuthority,
    WalletRelationshipType,
    WalletRole,
)
from app.schemas.scan_result import (
    WalletFundingData,
    WalletGraphData,
    WalletGraphEdge,
    WalletGraphNode,
    WalletIntelligenceData,
    WalletOwnershipData,
    WalletReputationData,
    WalletRoleNode,
)


@dataclass(frozen=True, slots=True)
class WalletAnalysisContext:
    """Governance and liquidity inputs for wallet intelligence."""

    chain_id: int
    contract_address: str
    admin_address: str | None
    admin_type: AdminType | None
    owner_address: str | None
    owner_type: AdminType | None
    governance_ownership_address: str | None
    is_timelock: bool
    upgrade_authority: UpgradeAuthority | None
    lp_owner: str | None


def resolve_ownership(
    context: WalletAnalysisContext,
    *,
    deployer: str | None,
) -> WalletOwnershipData:
    """Map governance and on-chain findings to wallet roles."""
    creator = deployer
    owner = context.governance_ownership_address or context.owner_address
    proxy_admin = context.admin_address if context.admin_address else None
    treasury: str | None = None

    multisig: str | None = None
    if context.admin_type == AdminType.MULTISIG and context.admin_address:
        multisig = context.admin_address
    elif context.owner_type == AdminType.MULTISIG and context.owner_address:
        multisig = context.owner_address

    timelock: str | None = None
    if context.is_timelock:
        timelock = context.owner_address or context.admin_address

    roles: list[WalletRoleNode] = []
    if creator:
        roles.append(WalletRoleNode(address=creator, role=WalletRole.CREATOR))
    if deployer and deployer != creator:
        roles.append(WalletRoleNode(address=deployer, role=WalletRole.DEPLOYER))
    elif deployer:
        roles.append(WalletRoleNode(address=deployer, role=WalletRole.DEPLOYER))
    if owner:
        roles.append(WalletRoleNode(address=owner, role=WalletRole.OWNER))
    if proxy_admin:
        roles.append(WalletRoleNode(address=proxy_admin, role=WalletRole.PROXY_ADMIN))
    if treasury:
        roles.append(WalletRoleNode(address=treasury, role=WalletRole.TREASURY))
    if multisig:
        roles.append(WalletRoleNode(address=multisig, role=WalletRole.MULTISIG))
    if timelock:
        roles.append(WalletRoleNode(address=timelock, role=WalletRole.TIMELOCK))
    if context.lp_owner:
        roles.append(WalletRoleNode(address=context.lp_owner, role=WalletRole.LP_OWNER))

    return WalletOwnershipData(
        creator=creator,
        deployer=deployer,
        owner=owner,
        proxy_admin=proxy_admin,
        treasury=treasury,
        multisig=multisig,
        timelock=timelock,
        upgrade_authority=context.upgrade_authority,
        roles=roles,
    )


def build_funding(
    deployer: str | None,
    deployer_transactions: list[ExplorerTransaction],
    creation_tx: ExplorerTransaction | None,
) -> WalletFundingData:
    """Analyze deployer funding history."""
    if deployer is None:
        return WalletFundingData()

    funding_tx = find_first_inbound_funding(deployer, deployer_transactions)
    funding_wallet = funding_tx.from_address if funding_tx else None
    source_type = classify_funding_source(funding_wallet)

    return WalletFundingData(
        first_funding_tx_hash=funding_tx.hash if funding_tx else None,
        funding_wallet=funding_wallet,
        funding_source=source_type,
        is_fresh_wallet=is_fresh_wallet(deployer_transactions),
        deployer_tx_count=len(deployer_transactions),
        contract_creation_tx_hash=creation_tx.hash if creation_tx else None,
        contract_creation_block=creation_tx.block_number if creation_tx else None,
    )


def build_reputation(result: WalletReputationResult) -> WalletReputationData:
    return WalletReputationData(
        known_scam=result.known_scam,
        phishing=result.phishing,
        sanctioned=result.sanctioned,
        exploit_related=result.exploit_related,
        confidence=result.confidence,
    )


def build_relationship_graph(
    contract_address: str,
    ownership: WalletOwnershipData,
    funding: WalletFundingData,
) -> WalletGraphData:
    """Produce a graph-ready node/edge structure for the frontend."""
    nodes: dict[str, WalletGraphNode] = {
        contract_address.lower(): WalletGraphNode(
            id=contract_address.lower(),
            label="contract",
            role=None,
        )
    }
    edges: list[WalletGraphEdge] = []

    def add_node(address: str | None, role: WalletRole, label: str) -> None:
        if not address:
            return
        normalized = address.lower()
        if normalized not in nodes:
            nodes[normalized] = WalletGraphNode(id=normalized, label=label, role=role)

    add_node(ownership.deployer, WalletRole.DEPLOYER, "deployer")
    add_node(ownership.creator, WalletRole.CREATOR, "creator")
    add_node(ownership.owner, WalletRole.OWNER, "owner")
    add_node(ownership.proxy_admin, WalletRole.PROXY_ADMIN, "proxy_admin")
    add_node(ownership.treasury, WalletRole.TREASURY, "treasury")
    add_node(ownership.multisig, WalletRole.MULTISIG, "multisig")
    add_node(ownership.timelock, WalletRole.TIMELOCK, "timelock")

    lp_owner = next(
        (role.address for role in ownership.roles if role.role == WalletRole.LP_OWNER),
        None,
    )
    add_node(lp_owner, WalletRole.LP_OWNER, "lp_owner")

    if ownership.deployer:
        edges.append(
            WalletGraphEdge(
                source=ownership.deployer.lower(),
                target=contract_address.lower(),
                relationship=WalletRelationshipType.DEPLOYED,
            )
        )
    if ownership.owner:
        edges.append(
            WalletGraphEdge(
                source=ownership.owner.lower(),
                target=contract_address.lower(),
                relationship=WalletRelationshipType.CONTROLS,
            )
        )
    if ownership.proxy_admin:
        edges.append(
            WalletGraphEdge(
                source=ownership.proxy_admin.lower(),
                target=contract_address.lower(),
                relationship=WalletRelationshipType.ADMINISTERS,
            )
        )
    if funding.funding_wallet and ownership.deployer:
        edges.append(
            WalletGraphEdge(
                source=funding.funding_wallet.lower(),
                target=ownership.deployer.lower(),
                relationship=WalletRelationshipType.FUNDS,
            )
        )
    if lp_owner:
        edges.append(
            WalletGraphEdge(
                source=lp_owner.lower(),
                target=contract_address.lower(),
                relationship=WalletRelationshipType.HOLDS_LP,
            )
        )
    if (
        ownership.creator
        and lp_owner
        and ownership.creator.lower() == lp_owner.lower()
    ):
        edges.append(
            WalletGraphEdge(
                source=ownership.creator.lower(),
                target=lp_owner.lower(),
                relationship=WalletRelationshipType.OWNS,
            )
        )

    return WalletGraphData(nodes=list(nodes.values()), edges=edges)


def compute_wallet_risk_signals(
    ownership: WalletOwnershipData,
    funding: WalletFundingData,
    reputation: WalletReputationData,
) -> dict[str, bool]:
    """Derive boolean risk signals consumed by RiskEngine."""
    creator = (ownership.creator or ownership.deployer or "").lower()
    owner = (ownership.owner or "").lower()
    lp_owner = next(
        (role.address.lower() for role in ownership.roles if role.role == WalletRole.LP_OWNER),
        "",
    )

    creator_owns_majority = bool(
        creator
        and (
            (owner and creator == owner)
            or (lp_owner and creator == lp_owner)
        )
    )

    return {
        "deployer_is_fresh": funding.is_fresh_wallet,
        "creator_owns_majority": creator_owns_majority,
        "lp_owner_is_creator": bool(creator and lp_owner and creator == lp_owner),
        "exchange_funded_deployer": funding.funding_source == FundingSourceType.EXCHANGE,
        "tornado_funded_deployer": funding.funding_source == FundingSourceType.TORNADO,
        "treasury_is_multisig": ownership.multisig is not None,
        "wallet_known_scam": reputation.known_scam or reputation.sanctioned,
    }


def compute_wallet_risk_score(signals: dict[str, bool]) -> int:
    """Internal wallet sub-score 0–100 from M5.2 heuristics."""
    score = 0
    if signals.get("deployer_is_fresh"):
        score += 12
    if signals.get("creator_owns_majority"):
        score += 25
    if signals.get("lp_owner_is_creator"):
        score += 18
    if signals.get("exchange_funded_deployer"):
        score -= 5
    if signals.get("tornado_funded_deployer"):
        score += 35
    if signals.get("treasury_is_multisig"):
        score -= 10
    if signals.get("wallet_known_scam"):
        score += 40
    return max(0, min(score, 100))


def build_wallet_intelligence(
    context: WalletAnalysisContext,
    *,
    creation_tx: ExplorerTransaction | None,
    deployer_transactions: list[ExplorerTransaction],
    reputation_result: WalletReputationResult,
) -> WalletIntelligenceData:
    """Aggregate ownership, funding, reputation, and relationships."""
    deployer = creation_tx.from_address if creation_tx else None
    ownership = resolve_ownership(context, deployer=deployer)
    funding = build_funding(deployer, deployer_transactions, creation_tx)
    reputation = build_reputation(reputation_result)
    graph = build_relationship_graph(context.contract_address, ownership, funding)
    signals = compute_wallet_risk_signals(ownership, funding, reputation)
    wallet_risk_score = compute_wallet_risk_score(signals)

    return WalletIntelligenceData(
        ownership=ownership,
        funding=funding,
        reputation=reputation,
        graph=graph,
        wallet_risk_score=wallet_risk_score,
        deployer_is_fresh=signals["deployer_is_fresh"],
        creator_owns_majority=signals["creator_owns_majority"],
        lp_owner_is_creator=signals["lp_owner_is_creator"],
        exchange_funded_deployer=signals["exchange_funded_deployer"],
        tornado_funded_deployer=signals["tornado_funded_deployer"],
        treasury_is_multisig=signals["treasury_is_multisig"],
    )


def empty_wallet_intelligence() -> WalletIntelligenceData:
    return WalletIntelligenceData()
