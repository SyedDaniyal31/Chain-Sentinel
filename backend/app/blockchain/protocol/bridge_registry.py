"""Known bridge deployment registry for M6.2 protocol detection."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.protocol.defi_registry import source_contains_marker

__all__ = ("BridgeDeployment", "BRIDGE_DEPLOYMENTS", "match_bridge_deployments", "source_contains_marker")


@dataclass(frozen=True, slots=True)
class BridgeDeployment:
    """Known on-chain deployment for a cross-chain bridge component."""

    protocol: str
    role: str
    chain_id: int
    address: str


BRIDGE_DEPLOYMENTS: tuple[BridgeDeployment, ...] = (
    BridgeDeployment("LayerZero", "endpoint", 1, "0x66a71dcef29a0ffbdb3c6a460a3b5bc2251575"),
    BridgeDeployment("Wormhole", "core", 1, "0x98f3c9e6e3f36eaa832f396b124298900b640994"),
    BridgeDeployment("Stargate", "router", 1, "0x8731d54e9d02ca2863d457a8346a88afeca0e07"),
    BridgeDeployment("Circle CCTP", "messenger", 1, "0x0a991d191182e2b023275e980142aaaf265c455e"),
    BridgeDeployment("Axelar", "gateway", 1, "0x4f4495245920a2b2e19e634f733016ac2b12a581"),
    BridgeDeployment("Hyperlane", "mailbox", 1, "0xc005dc82818d67af737725b7844c7863d9f9a5e"),
    BridgeDeployment("LayerZero", "endpoint", 11155111, "0x6edce65403992e310a62460808c4b910d552f9f9"),
)


def match_bridge_deployments(chain_id: int, target_address: str) -> list[BridgeDeployment]:
    """Return bridge registry deployments matching the target address on a chain."""
    normalized = target_address.lower()
    return [
        deployment
        for deployment in BRIDGE_DEPLOYMENTS
        if deployment.chain_id == chain_id and deployment.address.lower() == normalized
    ]
