"""OpenZeppelin and governance framework detection for M6.0."""

from __future__ import annotations

from web3 import Web3

from app.blockchain.access_control import GET_ROLE_ADMIN_SELECTOR, HAS_ROLE_SELECTOR
from app.blockchain.governance_patterns import PENDING_OWNER_SELECTOR
from app.blockchain.protocol.models import FrameworkDetection, ProtocolFramework
from app.blockchain.timelock import GET_MIN_DELAY_SELECTOR

GET_MIN_DELAY_BYTES = bytes.fromhex(GET_MIN_DELAY_SELECTOR[2:])

OWNABLE_OWNER_SELECTOR = Web3.keccak(text="owner()")[:4]
OWNABLE_TRANSFER_OWNERSHIP_SELECTOR = Web3.keccak(text="transferOwnership(address)")[:4]
PAUSE_SELECTOR = Web3.keccak(text="pause()")[:4]
UNPAUSE_SELECTOR = Web3.keccak(text="unpause()")[:4]
TIMELOCK_SCHEDULE_SELECTOR = Web3.keccak(text="schedule(address,uint256,bytes,bytes32,bytes32,uint256)")[:4]


def detect_frameworks(bytecode: bytes, *, is_timelock_hint: bool = False) -> list[FrameworkDetection]:
    """Detect OpenZeppelin-style framework patterns from bytecode selectors."""
    if not bytecode:
        return []

    results: list[FrameworkDetection] = []

    if _has_ownable(bytecode):
        reason = "Bytecode exposes owner() and transferOwnership(address) selectors"
        if PENDING_OWNER_SELECTOR in bytecode:
            reason = "Bytecode exposes Ownable2Step pendingOwner() in addition to owner()"
        results.append(
            FrameworkDetection(
                framework=ProtocolFramework.OPENZEPPELIN_OWNABLE,
                detected=True,
                reason=reason,
                confidence="high",
            )
        )

    if GET_ROLE_ADMIN_SELECTOR in bytecode and HAS_ROLE_SELECTOR in bytecode:
        results.append(
            FrameworkDetection(
                framework=ProtocolFramework.OPENZEPPELIN_ACCESS_CONTROL,
                detected=True,
                reason="Bytecode exposes AccessControl hasRole/getRoleAdmin selectors",
                confidence="high",
            )
        )

    if PAUSE_SELECTOR in bytecode and UNPAUSE_SELECTOR in bytecode:
        results.append(
            FrameworkDetection(
                framework=ProtocolFramework.OPENZEPPELIN_PAUSABLE,
                detected=True,
                reason="Bytecode exposes Pausable pause/unpause selectors",
                confidence="high",
            )
        )

    if is_timelock_hint or _has_timelock_controller(bytecode):
        results.append(
            FrameworkDetection(
                framework=ProtocolFramework.OPENZEPPELIN_TIMELOCK_CONTROLLER,
                detected=True,
                reason="Bytecode exposes TimelockController getMinDelay or schedule selectors",
                confidence="high" if GET_MIN_DELAY_BYTES in bytecode else "medium",
            )
        )

    return results


def _has_ownable(bytecode: bytes) -> bool:
    return OWNABLE_OWNER_SELECTOR in bytecode and OWNABLE_TRANSFER_OWNERSHIP_SELECTOR in bytecode


def _has_timelock_controller(bytecode: bytes) -> bool:
    return GET_MIN_DELAY_BYTES in bytecode or TIMELOCK_SCHEDULE_SELECTOR in bytecode
