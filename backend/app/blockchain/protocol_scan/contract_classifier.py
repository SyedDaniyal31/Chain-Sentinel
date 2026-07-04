"""Protocol contract role classification (M8.1)."""

from __future__ import annotations

from app.blockchain.protocol.bridge_registry import match_bridge_deployments
from app.blockchain.protocol.defi_registry import match_deployments
from app.blockchain.protocol.governance_registry import match_governance_deployments
from app.blockchain.protocol.vault_registry import match_vault_deployments
from app.blockchain.protocol_scan.models import ProtocolContract, ProtocolRole
from app.blockchain.protocol_scan.provider import ContractProbeResult
from app.models.enums import GovernanceType
from app.schemas.scan_result import GovernanceAnalysisData, ProtocolIntelligenceData


class ProtocolContractClassifier:
    """Map probe and analyzer outputs to protocol roles with confidence scores."""

    def classify_root(self, probe: ContractProbeResult) -> ProtocolContract:
        return ProtocolContract(
            address=probe.address,
            role=ProtocolRole.ROOT,
            confidence=95,
            detection_source="discovery.root",
        )

    def classify_probe(
        self,
        probe: ContractProbeResult,
        *,
        default_role: ProtocolRole = ProtocolRole.UNKNOWN,
        detection_source: str = "discovery.probe",
        confidence: int = 60,
    ) -> ProtocolContract:
        role, score, source = self._resolve_role(probe, default_role, detection_source, confidence)
        return ProtocolContract(
            address=probe.address,
            role=role,
            confidence=score,
            detection_source=source,
            metadata=self._build_metadata(probe),
        )

    def classify_from_registry(
        self,
        address: str,
        chain_id: int,
    ) -> ProtocolContract | None:
        defi_matches = match_deployments(chain_id, address)
        if defi_matches:
            deployment = defi_matches[0]
            return ProtocolContract(
                address=address,
                role=_DEFI_ROLE_MAP.get(deployment.role, ProtocolRole.UNKNOWN),
                confidence=92,
                detection_source="registry.deployment",
                metadata={
                    "protocol": deployment.protocol,
                    "registry_role": deployment.role,
                    "chain_id": chain_id,
                },
            )

        bridge_matches = match_bridge_deployments(chain_id, address)
        if bridge_matches:
            deployment = bridge_matches[0]
            return ProtocolContract(
                address=address,
                role=_BRIDGE_ROLE_MAP.get(deployment.role, ProtocolRole.BRIDGE),
                confidence=92,
                detection_source="registry.deployment",
                metadata={
                    "protocol": deployment.protocol,
                    "registry_role": deployment.role,
                    "chain_id": chain_id,
                },
            )

        vault_matches = match_vault_deployments(chain_id, address)
        if vault_matches:
            deployment = vault_matches[0]
            return ProtocolContract(
                address=address,
                role=ProtocolRole.VAULT,
                confidence=92,
                detection_source="registry.deployment",
                metadata={
                    "protocol": deployment.protocol,
                    "registry_role": deployment.vault_type,
                    "chain_id": chain_id,
                },
            )

        governance_matches = match_governance_deployments(chain_id, address)
        if governance_matches:
            deployment = governance_matches[0]
            return ProtocolContract(
                address=address,
                role=_GOVERNANCE_ROLE_MAP.get(deployment.role, ProtocolRole.GOVERNOR),
                confidence=92,
                detection_source="registry.deployment",
                metadata={
                    "protocol": deployment.protocol,
                    "registry_role": deployment.role,
                    "chain_id": chain_id,
                },
            )
        return None

    def classify_from_intelligence(
        self,
        address: str,
        intelligence: ProtocolIntelligenceData,
    ) -> ProtocolContract | None:
        if intelligence.name == "unknown" and intelligence.family == "unknown":
            return None
        role = _INTELLIGENCE_ROLE_MAP.get(intelligence.protocol_type, ProtocolRole.UNKNOWN)
        return ProtocolContract(
            address=address,
            role=role,
            confidence=intelligence.confidence.score or 55,
            detection_source="protocol_intelligence",
            metadata={
                "protocol_name": intelligence.name,
                "protocol_family": intelligence.family,
                "protocol_type": intelligence.protocol_type,
            },
        )

    def classify_governance_authority(
        self,
        address: str,
        governance: GovernanceAnalysisData,
        *,
        is_timelock: bool,
    ) -> ProtocolContract:
        if is_timelock or governance.governance_type == GovernanceType.TIMELOCK:
            role = ProtocolRole.TIMELOCK
        elif governance.governance_type in {GovernanceType.MULTISIG, GovernanceType.ACCESS_CONTROL}:
            role = ProtocolRole.GOVERNOR
        else:
            role = ProtocolRole.GOVERNOR
        confidence = _confidence_from_level(governance.source_confidence.value)
        return ProtocolContract(
            address=address,
            role=role,
            confidence=confidence,
            detection_source="governance_analyzer",
            metadata={"governance_type": governance.governance_type.value},
        )

    def classify_proxy_implementation(
        self,
        proxy_address: str,
        implementation_address: str,
        *,
        confidence: int = 90,
    ) -> tuple[ProtocolContract, ProtocolContract]:
        proxy = ProtocolContract(
            address=proxy_address,
            role=ProtocolRole.PROXY,
            confidence=confidence,
            detection_source="proxy_resolution",
        )
        implementation = ProtocolContract(
            address=implementation_address,
            role=ProtocolRole.IMPLEMENTATION,
            confidence=confidence,
            detection_source="proxy_resolution",
        )
        return proxy, implementation

    def classify_treasury(self, address: str, *, confidence: int = 75) -> ProtocolContract:
        return ProtocolContract(
            address=address,
            role=ProtocolRole.TREASURY,
            confidence=confidence,
            detection_source="wallet_intelligence",
        )

    def _resolve_role(
        self,
        probe: ContractProbeResult,
        default_role: ProtocolRole,
        detection_source: str,
        confidence: int,
    ) -> tuple[ProtocolRole, int, str]:
        registry_contract = self.classify_from_registry(probe.address, probe.chain_id)
        if registry_contract is not None:
            return registry_contract.role, registry_contract.confidence, registry_contract.detection_source
        if probe.implementation_address and probe.address != probe.implementation_address:
            return ProtocolRole.PROXY, max(confidence, 85), "proxy_resolution"
        if probe.is_timelock:
            return ProtocolRole.TIMELOCK, max(confidence, 80), "source_inspection.timelock"
        if probe.verified_source and probe.verified_source.is_verified:
            return default_role, max(confidence, 70), "verified_source"
        return default_role, confidence, detection_source

    @staticmethod
    def _build_metadata(probe: ContractProbeResult) -> dict[str, str | bool | None]:
        return {
            "verified": bool(probe.verified_source and probe.verified_source.is_verified),
            "contract_name": probe.verified_source.contract_name if probe.verified_source else None,
            "implementation_address": probe.implementation_address,
            "admin_address": probe.admin_address,
            "is_timelock": probe.is_timelock,
        }


_DEFI_ROLE_MAP = {
    "factory": ProtocolRole.FACTORY,
    "router": ProtocolRole.ROUTER,
    "pool": ProtocolRole.POOL,
    "vault": ProtocolRole.VAULT,
    "market": ProtocolRole.POOL,
    "comptroller": ProtocolRole.GOVERNOR,
}

_BRIDGE_ROLE_MAP = {
    "endpoint": ProtocolRole.BRIDGE,
    "core": ProtocolRole.BRIDGE,
    "router": ProtocolRole.BRIDGE,
    "messenger": ProtocolRole.MESSENGER,
    "gateway": ProtocolRole.BRIDGE,
    "mailbox": ProtocolRole.BRIDGE,
}

_VAULT_ROLE_MAP = {
    "erc4626 vault": ProtocolRole.VAULT,
    "yield vault": ProtocolRole.VAULT,
    "yield token": ProtocolRole.VAULT,
    "restaking vault": ProtocolRole.VAULT,
}

_GOVERNANCE_ROLE_MAP = {
    "governor": ProtocolRole.GOVERNOR,
    "timelock": ProtocolRole.TIMELOCK,
    "multisig": ProtocolRole.GOVERNOR,
}

_INTELLIGENCE_ROLE_MAP = {
    "upgradeable_proxy": ProtocolRole.PROXY,
    "minimal_proxy": ProtocolRole.PROXY,
    "token_vault": ProtocolRole.VAULT,
    "timelock": ProtocolRole.TIMELOCK,
    "governance": ProtocolRole.GOVERNOR,
    "fungible_token": ProtocolRole.TOKEN,
}


def _confidence_from_level(level: str) -> int:
    return {"high": 85, "medium": 65, "low": 45}.get(level, 55)
