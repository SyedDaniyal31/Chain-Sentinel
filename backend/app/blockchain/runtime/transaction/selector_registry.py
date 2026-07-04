"""Function selector registry with fallback signatures (M9.1)."""

from __future__ import annotations

from dataclasses import dataclass

from app.blockchain.runtime.transaction.models import TransactionCategory


@dataclass(frozen=True, slots=True)
class SelectorEntry:
    """Known function selector metadata."""

    selector: str
    function_name: str
    signature: str
    category: TransactionCategory | None = None


SELECTOR_REGISTRY: dict[str, SelectorEntry] = {
    "095ea7b3": SelectorEntry("095ea7b3", "approve", "approve(address,uint256)", TransactionCategory.APPROVAL),
    "d505accf": SelectorEntry("d505accf", "permit", "permit(address,address,uint256,uint256,uint8,bytes32,bytes32)", TransactionCategory.APPROVAL),
    "a22cb465": SelectorEntry("a22cb465", "setApprovalForAll", "setApprovalForAll(address,bool)", TransactionCategory.APPROVAL),
    "a9059cbb": SelectorEntry("a9059cbb", "transfer", "transfer(address,uint256)", TransactionCategory.TRANSFER),
    "23b872dd": SelectorEntry("23b872dd", "transferFrom", "transferFrom(address,address,uint256)", TransactionCategory.TRANSFER),
    "42842e0e": SelectorEntry("42842e0e", "safeTransferFrom", "safeTransferFrom(address,address,uint256)", TransactionCategory.TRANSFER),
    "b88d4fde": SelectorEntry("b88d4fde", "safeTransferFrom", "safeTransferFrom(address,address,uint256,bytes)", TransactionCategory.TRANSFER),
    "f242432a": SelectorEntry("f242432a", "safeTransferFrom", "safeTransferFrom(address,address,uint256,uint256,bytes)", TransactionCategory.TRANSFER),
    "2eb2c2d6": SelectorEntry("2eb2c2d6", "safeBatchTransferFrom", "safeBatchTransferFrom(address,address,uint256[],uint256[],bytes)", TransactionCategory.TRANSFER),
    "3659cfe6": SelectorEntry("3659cfe6", "upgradeTo", "upgradeTo(address)", TransactionCategory.UPGRADE),
    "4f1ef286": SelectorEntry("4f1ef286", "upgradeToAndCall", "upgradeToAndCall(address,bytes)", TransactionCategory.UPGRADE),
    "9ded06df": SelectorEntry("9ded06df", "setImplementation", "setImplementation(address)", TransactionCategory.UPGRADE),
    "8456cb59": SelectorEntry("8456cb59", "pause", "pause()", TransactionCategory.GOVERNANCE),
    "3f4ba83a": SelectorEntry("3f4ba83a", "unpause", "unpause()", TransactionCategory.GOVERNANCE),
    "40c10f19": SelectorEntry("40c10f19", "mint", "mint(address,uint256)", TransactionCategory.MINT),
    "a0712d68": SelectorEntry("a0712d68", "mint", "mint(uint256)", TransactionCategory.MINT),
    "42966c68": SelectorEntry("42966c68", "burn", "burn(uint256)", TransactionCategory.BURN),
    "79cc6790": SelectorEntry("79cc6790", "burnFrom", "burnFrom(address,uint256)", TransactionCategory.BURN),
    "f2fde38b": SelectorEntry("f2fde38b", "transferOwnership", "transferOwnership(address)", TransactionCategory.GOVERNANCE),
    "715018a6": SelectorEntry("715018a6", "renounceOwnership", "renounceOwnership()", TransactionCategory.GOVERNANCE),
    "2f2ff15d": SelectorEntry("2f2ff15d", "grantRole", "grantRole(bytes32,address)", TransactionCategory.GOVERNANCE),
    "d547741f": SelectorEntry("d547741f", "revokeRole", "revokeRole(bytes32,address)", TransactionCategory.GOVERNANCE),
    "0121a88c": SelectorEntry("0121a88c", "propose", "propose(address[],uint256[],string[],bytes[])", TransactionCategory.GOVERNANCE),
    "56781388": SelectorEntry("56781388", "castVote", "castVote(uint256,uint8)", TransactionCategory.GOVERNANCE),
    "fe0d94c1": SelectorEntry("fe0d94c1", "execute", "execute(address[],uint256[],bytes[],bytes32)", TransactionCategory.GOVERNANCE),
    "f2a0ba21": SelectorEntry("f2a0ba21", "schedule", "schedule(address,uint256,bytes,bytes32,bytes32,uint256)", TransactionCategory.GOVERNANCE),
    "7ff36ab5": SelectorEntry("7ff36ab5", "swapExactETHForTokens", "swapExactETHForTokens(uint256,address[],address,uint256)", TransactionCategory.SWAP),
    "38ed1739": SelectorEntry("38ed1739", "swapExactTokensForTokens", "swapExactTokensForTokens(uint256,uint256,address[],address,uint256)", TransactionCategory.SWAP),
    "791ac947": SelectorEntry("791ac947", "swapExactTokensForETH", "swapExactTokensForETH(uint256,uint256,address[],address,uint256)", TransactionCategory.SWAP),
    "b6f9de95": SelectorEntry("b6f9de95", "swapExactETHForTokensSupportingFeeOnTransferTokens", "swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,address[],address,uint256)", TransactionCategory.SWAP),
    "e8e33700": SelectorEntry("e8e33700", "addLiquidity", "addLiquidity(address,address,uint256,uint256,uint256,uint256,address,uint256)", TransactionCategory.LIQUIDITY),
    "baa2abde": SelectorEntry("baa2abde", "removeLiquidity", "removeLiquidity(address,address,uint256,uint256,uint256,address,uint256)", TransactionCategory.LIQUIDITY),
    "5cffe9de": SelectorEntry("5cffe9de", "sendMessage", "sendMessage(uint16,bytes,uint256,address,address,bytes)", TransactionCategory.BRIDGE),
    "c4d66de8": SelectorEntry("c4d66de8", "initialize", "initialize(address)", TransactionCategory.DEPLOYMENT),
}


class SelectorRegistry:
    """Lookup helper for known function selectors."""

    def __init__(self, entries: dict[str, SelectorEntry] | None = None) -> None:
        self._entries = entries or SELECTOR_REGISTRY

    def lookup(self, selector: str) -> SelectorEntry | None:
        normalized = selector.lower().removeprefix("0x")
        if len(normalized) < 8:
            return None
        return self._entries.get(normalized[:8])

    def all_entries(self) -> tuple[SelectorEntry, ...]:
        return tuple(sorted(self._entries.values(), key=lambda item: item.selector))
