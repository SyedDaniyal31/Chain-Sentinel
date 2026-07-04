"""Enumerations and metadata keys for unified risk evidence (M7.1)."""

from __future__ import annotations

from enum import StrEnum


class EvidenceSource(StrEnum):
    """Analyzer or subsystem that produced the evidence."""

    GOVERNANCE = "governance"
    LIQUIDITY = "liquidity"
    WALLET = "wallet"
    PROTOCOL = "protocol"
    RELATIONSHIP = "relationship"
    THREAT_SURFACE = "threat_surface"
    PROXY = "proxy"
    CAPABILITY = "capability"
    HONEYPOT = "honeypot"
    SIMULATION = "simulation"
    CLASSIFICATION = "classification"
    SYSTEM = "system"


class EvidenceCategory(StrEnum):
    """Semantic grouping for downstream correlation."""

    UPGRADEABILITY = "upgradeability"
    AUTHORITY = "authority"
    CAPABILITY = "capability"
    HONEYPOT = "honeypot"
    LIQUIDITY = "liquidity"
    WALLET = "wallet"
    PROTOCOL = "protocol"
    RELATIONSHIP = "relationship"
    THREAT = "threat"
    CLASSIFICATION = "classification"
    CONFIDENCE = "confidence"
    SYSTEM = "system"


class EvidenceSeverity(StrEnum):
    """Normalized severity for a single evidence item."""

    INFO = "info"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EvidenceMetadataKey(StrEnum):
    """Well-known metadata keys attached to RiskEvidence."""

    SIGNAL = "signal"
    THREAT_WEIGHT = "threat_weight"
    CENTRALIZATION_WEIGHT = "centralization_weight"
    CONFIDENCE_WEIGHT = "confidence_weight"
    FORCE_THREAT_CRITICAL = "force_threat_critical"
    REASON_ONLY = "reason_only"
    ADMIN_TYPE = "admin_type"
    OWNER_TYPE = "owner_type"
    IS_TIMELOCK = "is_timelock"
    MIN_DELAY = "min_delay"
    DETECTION_METHOD = "detection_method"
    ENTITY_NAME = "entity_name"
    ENTITY_ADDRESS = "entity_address"
    RELATIONSHIP_TYPE = "relationship_type"
    ATTACK_PATH = "attack_path"
