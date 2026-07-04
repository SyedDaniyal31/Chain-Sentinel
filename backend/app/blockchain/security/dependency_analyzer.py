"""External dependency analysis for M6.4 threat surface intelligence."""

from __future__ import annotations

from app.blockchain.security.threat_models import DependencyCategory, ExternalDependency, ThreatSurfaceContext


def analyze_external_dependencies(context: ThreatSurfaceContext) -> list[ExternalDependency]:
    """Detect external protocol dependencies from protocol and relationship intelligence."""
    dependencies: dict[tuple[str, str], ExternalDependency] = {}

    category_items = (
        (DependencyCategory.BRIDGE, context.bridges),
        (DependencyCategory.ORACLE, context.oracles),
        (DependencyCategory.DEX, context.dexes),
        (DependencyCategory.VAULT, context.vaults),
        (DependencyCategory.GOVERNANCE, context.governance_protocols),
        (DependencyCategory.LENDING, context.lending),
    )

    for category, items in category_items:
        for item in items:
            name = str(item.get("name") or item.get("standard") or "unknown")
            role = str(item.get("role") or item.get("type") or item.get("marketplace") or "")
            confidence = int(item.get("confidence") or 70)
            _upsert(
                dependencies,
                ExternalDependency(
                    category=category,
                    name=name,
                    role=role,
                    confidence=confidence,
                    detection_source=f"protocol_intelligence.{category.value}",
                ),
            )

    if context.proxy_type not in {"none", "unknown"} or context.is_upgradeable:
        _upsert(
            dependencies,
            ExternalDependency(
                category=DependencyCategory.PROXY,
                name=context.proxy_type if context.proxy_type not in {"none", "unknown"} else "upgradeable_proxy",
                role="proxy",
                confidence=88 if context.is_upgradeable else 75,
                detection_source="protocol_intelligence.proxy",
                address=context.implementation_address,
            ),
        )

    if context.liquidity_has_liquidity and context.liquidity_primary_dex:
        _upsert(
            dependencies,
            ExternalDependency(
                category=DependencyCategory.DEX,
                name=context.liquidity_primary_dex,
                role="liquidity_pool",
                confidence=83,
                detection_source="liquidity_intelligence.primary_dex",
                address=context.liquidity_pair_address,
            ),
        )

    if context.governance_type and context.governance_type not in {"none", "unknown"}:
        _upsert(
            dependencies,
            ExternalDependency(
                category=DependencyCategory.GOVERNANCE,
                name=context.governance_type,
                role="governance",
                confidence=80,
                detection_source="governance_intelligence.governance_type",
            ),
        )

    return sorted(dependencies.values(), key=lambda item: item.confidence, reverse=True)


def _upsert(
    dependencies: dict[tuple[str, str], ExternalDependency],
    candidate: ExternalDependency,
) -> None:
    key = (candidate.category.value, candidate.name.lower())
    existing = dependencies.get(key)
    if existing is None or candidate.confidence > existing.confidence:
        dependencies[key] = candidate
