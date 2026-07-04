"""Framework detector unit tests (M6.0)."""

from web3 import Web3

from app.blockchain.protocol.framework_detector import detect_frameworks

OWNABLE_OWNER = Web3.keccak(text="owner()")[:4]
OWNABLE_TRANSFER = Web3.keccak(text="transferOwnership(address)")[:4]
PAUSE = Web3.keccak(text="pause()")[:4]
UNPAUSE = Web3.keccak(text="unpause()")[:4]
HAS_ROLE = Web3.keccak(text="hasRole(bytes32,address)")[:4]
GET_ROLE_ADMIN = Web3.keccak(text="getRoleAdmin(bytes32)")[:4]


def test_detect_openzeppelin_ownable() -> None:
    bytecode = b"\x60\x80" + OWNABLE_OWNER + OWNABLE_TRANSFER
    results = detect_frameworks(bytecode)
    frameworks = {item.framework.value for item in results if item.detected}
    assert "OpenZeppelin Ownable" in frameworks


def test_detect_openzeppelin_pausable() -> None:
    bytecode = b"\x60\x80" + PAUSE + UNPAUSE
    results = detect_frameworks(bytecode)
    frameworks = {item.framework.value for item in results if item.detected}
    assert "OpenZeppelin Pausable" in frameworks


def test_detect_openzeppelin_access_control() -> None:
    bytecode = b"\x60\x80" + HAS_ROLE + GET_ROLE_ADMIN
    results = detect_frameworks(bytecode)
    frameworks = {item.framework.value for item in results if item.detected}
    assert "OpenZeppelin AccessControl" in frameworks


def test_detect_timelock_with_hint() -> None:
    results = detect_frameworks(b"\x60\x80", is_timelock_hint=True)
    frameworks = {item.framework.value for item in results if item.detected}
    assert "OpenZeppelin TimelockController" in frameworks
