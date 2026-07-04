"""Protocol intelligence aggregation builder (M6.0 + M6.1 + M6.2)."""

from __future__ import annotations

from web3 import AsyncWeb3

from app.blockchain.protocol.bridge_detector import detect_bridges
from app.blockchain.protocol.confidence_engine import compute_confidence
from app.blockchain.protocol.dex_detector import detect_dexes
from app.blockchain.protocol.framework_detector import detect_frameworks
from app.blockchain.protocol.governance_detector import detect_governance
from app.blockchain.protocol.lending_detector import detect_lending
from app.blockchain.protocol.models import ProtocolDetectionBundle, ProtocolDetectionContext
from app.blockchain.protocol.nft_detector import detect_nfts
from app.blockchain.protocol.oracle_detector import detect_oracles
from app.blockchain.protocol.protocol_detector import (
    build_detection_reasons,
    resolve_protocol_identity,
)
from app.blockchain.protocol.protocol_registry import detect_integrations
from app.blockchain.protocol.proxy_detector import detect_proxy
from app.blockchain.protocol.standards_detector import detect_standards
from app.blockchain.protocol.vault_detector import detect_vaults
from app.schemas.scan_result import (
    BridgeIntegrationData,
    DexIntegrationData,
    GovernanceIntegrationData,
    LendingIntegrationData,
    NftIntegrationData,
    OracleIntegrationData,
    ProtocolConfidenceData,
    ProtocolIntelligenceData,
    VaultIntegrationData,
)


async def build_protocol_intelligence(
    web3: AsyncWeb3,
    context: ProtocolDetectionContext,
) -> ProtocolIntelligenceData:
    """Run all protocol detectors and shape API output."""
    if not context.bytecode and not context.logic_bytecode:
        return ProtocolIntelligenceData()

    standards = detect_standards(context.logic_bytecode)
    frameworks = detect_frameworks(context.logic_bytecode, is_timelock_hint=context.is_timelock_hint)
    proxy = await detect_proxy(web3, context)
    integrations = detect_integrations(context.logic_bytecode)
    dexes = detect_dexes(context)
    lending = detect_lending(context)
    oracles = detect_oracles(context)
    bridges = detect_bridges(context)
    vaults = detect_vaults(context)
    nfts = detect_nfts(context)
    governance = detect_governance(context)

    bundle = ProtocolDetectionBundle(
        standards=standards,
        frameworks=frameworks,
        proxy=proxy,
        integrations=integrations,
        dexes=dexes,
        lending=lending,
        oracles=oracles,
        bridges=bridges,
        vaults=vaults,
        nfts=nfts,
        governance=governance,
        verified_source_code=context.verified_source_code,
        contract_name=context.contract_name,
    )
    bundle.detection_reasons = build_detection_reasons(bundle)

    family, name, protocol_type = resolve_protocol_identity(bundle)
    confidence = compute_confidence(bundle)

    return ProtocolIntelligenceData(
        protocol_family=family.value,
        protocol_name=name,
        protocol_type=protocol_type.value,
        family=family.value,
        name=name,
        standards=[item.standard.value for item in standards if item.detected],
        frameworks=[item.framework.value for item in frameworks if item.detected],
        integrations=integrations,
        proxy_type=proxy.proxy_kind.value if proxy else "none",
        dexes=[
            DexIntegrationData(name=item.name, role=item.role, confidence=item.confidence)
            for item in dexes
        ],
        lending=[
            LendingIntegrationData(name=item.name, role=item.role, confidence=item.confidence)
            for item in lending
        ],
        oracles=[
            OracleIntegrationData(name=item.name, confidence=item.confidence)
            for item in oracles
        ],
        bridges=[
            BridgeIntegrationData(name=item.name, role=item.role, confidence=item.confidence)
            for item in bridges
        ],
        vaults=[
            VaultIntegrationData(name=item.name, type=item.type, confidence=item.confidence)
            for item in vaults
        ],
        nfts=[
            NftIntegrationData(
                standard=item.standard,
                marketplace=item.marketplace,
                confidence=item.confidence,
            )
            for item in nfts
        ],
        governance=[
            GovernanceIntegrationData(name=item.name, confidence=item.confidence)
            for item in governance
        ],
        confidence=ProtocolConfidenceData(score=confidence.score, level=confidence.level),
        detection_reasons=bundle.detection_reasons,
    )
