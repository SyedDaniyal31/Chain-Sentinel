"""Known vault deployment registry for M6.2 protocol detection."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker

__all__ = ("VaultDeployment", "VAULT_DEPLOYMENTS", "match_vault_deployments", "source_contains_marker")


@dataclass(frozen=True, slots=True)
class VaultDeployment:
    """Known on-chain deployment for a yield vault component."""

    protocol: str
    vault_type: str
    chain_id: int
    address: str


VAULT_DEPLOYMENTS: tuple[VaultDeployment, ...] = (
    VaultDeployment("Yearn", "ERC4626 Vault", 1, "0x5f18c75abdae578b483e0628919e8f13bd7f7d0a"),
    VaultDeployment("Beefy", "Yield Vault", 1, "0x850b1d5574be5c99288215c684b1881ff85559e"),
    VaultDeployment("Pendle", "Yield Token", 1, "0x808507121b80c02388fad14726482e061b8da827"),
    VaultDeployment("EigenLayer", "Restaking Vault", 1, "0x85864637863b2a5773840591b90c1950e2cfe11"),
)


def match_vault_deployments(chain_id: int, target_address: str) -> list[VaultDeployment]:
    """Return vault registry deployments matching the target address on a chain."""
    normalized = target_address.lower()
    return [
        deployment
        for deployment in VAULT_DEPLOYMENTS
        if deployment.chain_id == chain_id and deployment.address.lower() == normalized
    ]
