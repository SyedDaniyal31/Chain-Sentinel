"""Attack path inference for M6.4 threat surface intelligence."""

from __future__ import annotations

from app.blockchain.security.threat_models import (
    AttackPath,
    ExternalDependency,
    PrivilegedEntity,
    ThreatSurfaceContext,
    TrustBoundary,
)
from app.blockchain.security.threat_registry import ATTACK_PATH_TEMPLATES, build_attack_path_from_template


def build_attack_paths(
    context: ThreatSurfaceContext,
    dependencies: list[ExternalDependency],
    boundaries: list[TrustBoundary],
    privileged: list[PrivilegedEntity],
) -> list[AttackPath]:
    """Infer multi-hop attack paths from dependencies, boundaries, and privileged entities."""
    paths: dict[str, AttackPath] = {}
    categories = {dep.category.value for dep in dependencies}

    for template in ATTACK_PATH_TEMPLATES:
        if not _template_matches(template, context, categories, privileged):
            continue
        boost = _confidence_boost(template.key, context, dependencies, privileged)
        paths[template.key] = build_attack_path_from_template(template, confidence_boost=boost)

    if context.honeypot_is_suspected or context.honeypot_is_confirmed:
        paths["honeypot_exit"] = AttackPath(
            name="Privileged Controller to Trading Restriction to Exit Block",
            steps=("Privileged Controller", "Trading Restriction", "Exit Block"),
            confidence=90 if context.honeypot_is_confirmed else 75,
            detection_source="honeypot_intelligence.summary",
        )

    if context.mint_capability and privileged:
        paths["mint_inflation"] = AttackPath(
            name="Privileged Controller to Mint to Supply Inflation",
            steps=("Privileged Controller", "Mint", "Supply Inflation"),
            confidence=80,
            detection_source="capability_intelligence.mint",
        )

    for relationship in context.relationships:
        rel_type = str(relationship.get("relationship_type") or "")
        if rel_type == "UPGRADEABLE_BY":
            key = f"rel_upgrade_{relationship.get('target')}"
            paths[key] = AttackPath(
                name=f"Upgrade Path via {relationship.get('target')}",
                steps=("Target Contract", str(relationship.get("target")), "Implementation"),
                confidence=int(relationship.get("confidence") or 78),
                detection_source="relationship_intelligence.upgradeable_by",
            )

    return sorted(paths.values(), key=lambda item: item.confidence, reverse=True)


def _template_matches(
    template,
    context: ThreatSurfaceContext,
    categories: set[str],
    privileged: list[PrivilegedEntity],
) -> bool:
    if not template.required_categories:
        return True
    if all(cat in categories for cat in template.required_categories):
        return True
    if template.key == "owner_proxy_impl_funds":
        return context.is_upgradeable and bool(privileged)
    if template.key == "governor_upgrade_impl":
        return context.is_upgradeable and bool(context.governance_protocols or context.has_timelock)
    return False


def _confidence_boost(
    template_key: str,
    context: ThreatSurfaceContext,
    dependencies: list[ExternalDependency],
    privileged: list[PrivilegedEntity],
) -> int:
    boost = 0
    if context.is_verified:
        boost += 3
    if privileged:
        boost += 5
    if template_key == "oracle_price_vault" and any(dep.category.value == "oracle" for dep in dependencies):
        boost += 8
    if template_key == "bridge_message_mint" and context.mint_capability:
        boost += 6
    return boost
