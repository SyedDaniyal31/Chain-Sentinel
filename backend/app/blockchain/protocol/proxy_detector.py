"""Upgrade proxy pattern detection for M6.0 protocol intelligence."""

from __future__ import annotations

from web3 import AsyncWeb3, Web3

from app.blockchain.eip1967 import (
    EIP1967_ADMIN_SLOT,
    EIP1967_BEACON_SLOT,
    EIP1967_IMPLEMENTATION_SLOT,
    parse_eip1967_admin,
    parse_eip1967_implementation,
)
from app.blockchain.protocol.models import ProtocolDetectionContext, ProtocolProxyKind, ProxyDetection
from app.core.validators import normalize_eth_address

# EIP-1167 minimal proxy init code prefix.
MINIMAL_PROXY_PREFIX = bytes.fromhex("363d3d373d3d3d363d73")

# UUPS upgrade selectors on implementation logic.
UUPS_UPGRADE_TO_SELECTOR = Web3.keccak(text="upgradeTo(address)")[:4]
UUPS_UPGRADE_TO_AND_CALL_SELECTOR = Web3.keccak(text="upgradeToAndCall(address,bytes)")[:4]


def detect_minimal_proxy_from_bytecode(bytecode: bytes) -> ProxyDetection | None:
    """Detect EIP-1167 minimal clone proxies from init code pattern."""
    if not bytecode:
        return None
    if MINIMAL_PROXY_PREFIX in bytecode or bytecode.startswith(MINIMAL_PROXY_PREFIX):
        return ProxyDetection(
            proxy_kind=ProtocolProxyKind.MINIMAL_PROXY,
            detected=True,
            reason="Runtime bytecode matches EIP-1167 minimal proxy clone pattern",
            confidence="high",
        )
    return None


def detect_uups_from_logic_bytecode(logic_bytecode: bytes) -> bool:
    """Return True when logic bytecode exposes UUPS upgrade selectors."""
    return (
        UUPS_UPGRADE_TO_SELECTOR in logic_bytecode
        or UUPS_UPGRADE_TO_AND_CALL_SELECTOR in logic_bytecode
    )


async def detect_proxy(
    web3: AsyncWeb3,
    context: ProtocolDetectionContext,
) -> ProxyDetection:
    """Detect ERC-1967, beacon, transparent, UUPS, and minimal proxy patterns."""
    minimal = detect_minimal_proxy_from_bytecode(context.bytecode)
    if minimal is not None:
        return minimal

    normalized = normalize_eth_address(context.target_address)
    checksum = AsyncWeb3.to_checksum_address(normalized)

    implementation_address = context.implementation_address
    admin_address = context.admin_address
    beacon_address: str | None = None

    try:
        beacon_word = await web3.eth.get_storage_at(checksum, EIP1967_BEACON_SLOT)
        beacon_address = parse_eip1967_implementation(bytes(beacon_word))
    except Exception:
        beacon_address = None

    if beacon_address is not None:
        return ProxyDetection(
            proxy_kind=ProtocolProxyKind.BEACON,
            detected=True,
            reason="EIP-1967 beacon storage slot contains a non-zero beacon address",
            confidence="high",
        )

    if implementation_address is None:
        try:
            impl_word = await web3.eth.get_storage_at(checksum, EIP1967_IMPLEMENTATION_SLOT)
            implementation_address = parse_eip1967_implementation(bytes(impl_word))
        except Exception:
            implementation_address = None

    if implementation_address is None:
        return ProxyDetection(
            proxy_kind=ProtocolProxyKind.NONE,
            detected=False,
            reason="No EIP-1967 implementation slot or minimal proxy pattern detected",
            confidence="medium",
        )

    if admin_address is None:
        try:
            admin_word = await web3.eth.get_storage_at(checksum, EIP1967_ADMIN_SLOT)
            admin_address = parse_eip1967_admin(bytes(admin_word))
        except Exception:
            admin_address = None

    if admin_address is not None:
        return ProxyDetection(
            proxy_kind=ProtocolProxyKind.TRANSPARENT,
            detected=True,
            reason="EIP-1967 implementation and admin slots populated (transparent proxy)",
            confidence="high",
        )

    logic_bytecode = context.logic_bytecode
    if detect_uups_from_logic_bytecode(logic_bytecode):
        return ProxyDetection(
            proxy_kind=ProtocolProxyKind.UUPS,
            detected=True,
            reason="EIP-1967 implementation slot without admin slot; logic exposes UUPS upgradeTo",
            confidence="high",
        )

    return ProxyDetection(
        proxy_kind=ProtocolProxyKind.ERC1967,
        detected=True,
        reason="EIP-1967 implementation slot populated without transparent admin slot",
        confidence="medium",
    )
