"""Governance pattern fingerprints for bytecode analysis."""

from web3 import Web3

from app.blockchain.access_control import GET_ROLE_ADMIN_SELECTOR, HAS_ROLE_SELECTOR

# OpenZeppelin Ownable2Step
PENDING_OWNER_SELECTOR = Web3.keccak(text="pendingOwner()")[:4]

# OpenZeppelin ProxyAdmin
PROXY_ADMIN_UPGRADE_SELECTOR = Web3.keccak(text="upgrade(address,address)")[:4]
PROXY_ADMIN_CHANGE_ADMIN_SELECTOR = Web3.keccak(text="changeProxyAdmin(address,address)")[:4]

PROXY_ADMIN_SELECTORS: frozenset[bytes] = frozenset(
    {
        PROXY_ADMIN_UPGRADE_SELECTOR,
        PROXY_ADMIN_CHANGE_ADMIN_SELECTOR,
    }
)


def has_ownable2step_selectors(bytecode: bytes) -> bool:
    """Detect Ownable2Step via pendingOwner() selector presence."""
    return PENDING_OWNER_SELECTOR in bytecode


def has_proxy_admin_selectors(bytecode: bytes) -> bool:
    """Detect ProxyAdmin-style upgrade management selectors."""
    return any(selector in bytecode for selector in PROXY_ADMIN_SELECTORS)


def has_access_control_bytecode(bytecode: bytes) -> bool:
    """Detect AccessControl via hasRole/getRoleAdmin selectors."""
    return GET_ROLE_ADMIN_SELECTOR in bytecode and HAS_ROLE_SELECTOR in bytecode
