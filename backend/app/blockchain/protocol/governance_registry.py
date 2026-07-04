"""Known governance deployment registry for M6.2 protocol detection."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker

__all__ = ("GovernanceDeployment", "GOVERNANCE_DEPLOYMENTS", "match_governance_deployments", "source_contains_marker")


@dataclass(frozen=True, slots=True)
class GovernanceDeployment:
    """Known on-chain deployment for a governance contract."""

    protocol: str
    role: str
    chain_id: int
    address: str


GOVERNANCE_DEPLOYMENTS: tuple[GovernanceDeployment, ...] = (
    GovernanceDeployment("Governor Bravo", "governor", 1, "0x30948667925aaad57af76230dada8050db471066"),
    GovernanceDeployment("Compound Governor", "governor", 1, "0x30948667925aaad57af76230dada8050db471066"),
    GovernanceDeployment("OpenZeppelin Governor", "governor", 1, "0x408854448c7f4771883bc9f6a328f585a1c0c572"),
    GovernanceDeployment("Timelock Governor", "timelock", 1, "0x3d9819210a31b4961b5e55aaf6cf52de0a3b83b7"),
)


def match_governance_deployments(chain_id: int, target_address: str) -> list[GovernanceDeployment]:
    """Return governance registry deployments matching the target address on a chain."""
    normalized = target_address.lower()
    return [
        deployment
        for deployment in GOVERNANCE_DEPLOYMENTS
        if deployment.chain_id == chain_id and deployment.address.lower() == normalized
    ]
