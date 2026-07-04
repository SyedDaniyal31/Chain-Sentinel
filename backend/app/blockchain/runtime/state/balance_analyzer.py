"""Balance transition analysis (M9.3)."""

from __future__ import annotations

from app.blockchain.runtime.state.event_state_mapper import EventStateMapper
from app.blockchain.runtime.state.models import BalanceAssetType, BalanceChange, RawStateTransition


class BalanceAnalyzer:
    """Detect ETH and token balance transitions."""

    def __init__(self, event_mapper: EventStateMapper | None = None) -> None:
        self._event_mapper = event_mapper or EventStateMapper()

    def analyze(self, transition: RawStateTransition) -> tuple[BalanceChange, ...]:
        changes: list[BalanceChange] = []

        for diff in transition.balance_diffs:
            if diff.before == diff.after:
                continue
            changes.append(
                BalanceChange(
                    asset_type=diff.asset_type,
                    contract_address=diff.contract_address.lower() if diff.contract_address else None,
                    account_address=diff.account_address.lower(),
                    before=diff.before,
                    after=diff.after,
                    delta=diff.after - diff.before,
                    token_id=diff.token_id,
                )
            )

        for event in self._event_mapper.map_logs(transition.logs):
            if event.event_kind.value == "transfer":
                asset_type = _asset_type_from_metadata(event.metadata)
                changes.append(
                    BalanceChange(
                        asset_type=asset_type,
                        contract_address=event.contract_address.lower(),
                        account_address=str(event.metadata.get("to", "")).lower(),
                        before=0,
                        after=int(event.metadata.get("value", 0)),
                        delta=int(event.metadata.get("value", 0)),
                        token_id=_optional_token_id(event.metadata, asset_type),
                        counterparty=str(event.metadata.get("from", "")).lower() or None,
                    )
                )

        return tuple(sorted(_dedupe_balance_changes(changes), key=_balance_sort_key))


def _asset_type_from_metadata(metadata: dict[str, object]) -> BalanceAssetType:
    raw = str(metadata.get("asset_type", "erc20")).lower()
    mapping = {
        "native": BalanceAssetType.NATIVE,
        "erc20": BalanceAssetType.ERC20,
        "erc721": BalanceAssetType.ERC721,
        "erc1155": BalanceAssetType.ERC1155,
    }
    return mapping.get(raw, BalanceAssetType.ERC20)


def _optional_token_id(metadata: dict[str, object], asset_type: BalanceAssetType) -> int | None:
    if asset_type not in {BalanceAssetType.ERC721, BalanceAssetType.ERC1155}:
        return None
    token_id = metadata.get("token_id")
    return int(token_id) if token_id is not None else int(metadata.get("value", 0))


def _dedupe_balance_changes(changes: list[BalanceChange]) -> list[BalanceChange]:
    seen: set[tuple[str, str, str, int | None]] = set()
    unique: list[BalanceChange] = []
    for change in changes:
        key = (
            change.asset_type.value,
            change.contract_address or "",
            change.account_address,
            change.token_id,
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(change)
    return unique


def _balance_sort_key(item: BalanceChange) -> tuple[str, str, str]:
    return (item.asset_type.value, item.contract_address or "", item.account_address)
