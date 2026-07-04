"""Threat inference rules and attack path templates (M6.4)."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.security.threat_models import AttackPath, DependencyCategory, PrivilegedEntityType


@dataclass(frozen=True, slots=True)
class AttackPathTemplate:
    """Template for inferring multi-hop attack paths."""

    key: str
    name: str
    steps: tuple[str, ...]
    base_confidence: int
    detection_source: str
    required_categories: tuple[str, ...] = ()


DEPENDENCY_CATEGORY_MAP: dict[str, DependencyCategory] = {
    "bridge": DependencyCategory.BRIDGE,
    "oracle": DependencyCategory.ORACLE,
    "dex": DependencyCategory.DEX,
    "vault": DependencyCategory.VAULT,
    "proxy": DependencyCategory.PROXY,
    "governance": DependencyCategory.GOVERNANCE,
    "lending": DependencyCategory.LENDING,
}


ATTACK_PATH_TEMPLATES: tuple[AttackPathTemplate, ...] = (
    AttackPathTemplate(
        key="owner_proxy_impl_funds",
        name="Owner to ProxyAdmin to Implementation to Funds",
        steps=("Owner", "ProxyAdmin", "Implementation", "Funds"),
        base_confidence=82,
        detection_source="threat_registry.upgrade_chain",
        required_categories=("proxy",),
    ),
    AttackPathTemplate(
        key="oracle_price_vault",
        name="Oracle to Price to Vault",
        steps=("Oracle", "Price Feed", "Vault"),
        base_confidence=80,
        detection_source="threat_registry.oracle_vault",
        required_categories=("oracle", "vault"),
    ),
    AttackPathTemplate(
        key="bridge_message_mint",
        name="Bridge to Message to Mint",
        steps=("Bridge", "Cross-chain Message", "Mint"),
        base_confidence=78,
        detection_source="threat_registry.bridge_mint",
        required_categories=("bridge",),
    ),
    AttackPathTemplate(
        key="governor_upgrade_impl",
        name="Governor to Upgrade to Implementation",
        steps=("Governor", "Upgrade", "Implementation"),
        base_confidence=84,
        detection_source="threat_registry.governance_upgrade",
        required_categories=("governance", "proxy"),
    ),
    AttackPathTemplate(
        key="dex_liquidity_drain",
        name="DEX to Liquidity Pool to Token Reserves",
        steps=("DEX Router", "Liquidity Pool", "Token Reserves"),
        base_confidence=76,
        detection_source="threat_registry.dex_liquidity",
        required_categories=("dex",),
    ),
)


PRIVILEGED_ENTITY_LABELS: dict[PrivilegedEntityType, str] = {
    PrivilegedEntityType.OWNER: "Owner",
    PrivilegedEntityType.PROXY_ADMIN: "Proxy Admin",
    PrivilegedEntityType.GOVERNOR: "Governor",
    PrivilegedEntityType.DAO: "DAO",
    PrivilegedEntityType.TIMELOCK: "Timelock",
    PrivilegedEntityType.SAFE: "Safe",
    PrivilegedEntityType.MULTISIG: "Multisig",
    PrivilegedEntityType.BRIDGE_RELAYER: "Bridge Relayer",
    PrivilegedEntityType.ORACLE_ADMIN: "Oracle Admin",
    PrivilegedEntityType.CAPABILITY_CONTROLLER: "Capability Controller",
}


def build_attack_path_from_template(
    template: AttackPathTemplate,
    *,
    confidence_boost: int = 0,
) -> AttackPath:
    return AttackPath(
        name=template.name,
        steps=template.steps,
        confidence=min(100, template.base_confidence + confidence_boost),
        detection_source=template.detection_source,
    )
