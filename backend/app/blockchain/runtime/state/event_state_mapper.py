"""Map execution logs to semantic state events (M9.3)."""

from __future__ import annotations

from app.blockchain.runtime.state.models import MappedEventKind, MappedStateEvent, RawStateLog

TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163caa673f6c72a25a0c726"
TOPIC_APPROVAL = "0x8c5be1e5ebec7d07bde6b468436436c9b6773938311887562a15482c6968b193"
TOPIC_OWNERSHIP_TRANSFERRED = "0x8be0079c531659141344cd1fd0a0f284194bc979c358836e638b052fb89f780a"
TOPIC_ROLE_GRANTED = "0x2f8788117e7eff1d1e114834a54296279b6a06646258199245ee975980667f482"
TOPIC_ROLE_REVOKED = "0xf6391f5c32d9c69d2a6998bef1fcbeafa92125de2ce89e3b7c76959d2e21c966"


class EventStateMapper:
    """Map low-level logs into semantic state transition events."""

    def map_logs(self, logs: tuple[RawStateLog, ...]) -> tuple[MappedStateEvent, ...]:
        mapped: list[MappedStateEvent] = []
        for log in logs:
            if not log.topics:
                continue
            topic0 = log.topics[0].lower()
            if topic0 == TOPIC_TRANSFER:
                mapped.append(_map_transfer(log))
            elif topic0 == TOPIC_APPROVAL:
                mapped.append(_map_approval(log))
            elif topic0 == TOPIC_OWNERSHIP_TRANSFERRED:
                mapped.append(_map_ownership_transferred(log))
            elif topic0 == TOPIC_ROLE_GRANTED:
                mapped.append(_map_role_event(log, MappedEventKind.ROLE_GRANTED))
            elif topic0 == TOPIC_ROLE_REVOKED:
                mapped.append(_map_role_event(log, MappedEventKind.ROLE_REVOKED))
        return tuple(sorted(mapped, key=lambda item: (item.event_kind.value, item.contract_address)))


def _map_transfer(log: RawStateLog) -> MappedStateEvent:
    asset_type = "erc721" if len(log.topics) >= 4 else "erc20"
    from_address = _topic_address(log.topics[1])
    to_address = _topic_address(log.topics[2])
    if asset_type == "erc721":
        token_id = int(log.topics[3], 16)
        value = token_id
    else:
        token_id = None
        value = _uint_from_data(log.data)
    return MappedStateEvent(
        event_kind=MappedEventKind.TRANSFER,
        contract_address=log.contract_address.lower(),
        metadata={
            "from": from_address,
            "to": to_address,
            "value": value,
            "token_id": token_id,
            "asset_type": asset_type,
        },
    )


def _map_approval(log: RawStateLog) -> MappedStateEvent:
    return MappedStateEvent(
        event_kind=MappedEventKind.APPROVAL,
        contract_address=log.contract_address.lower(),
        metadata={
            "owner": _topic_address(log.topics[1]),
            "spender": _topic_address(log.topics[2]),
            "value": _uint_from_data(log.data),
            "before": 0,
        },
    )


def _map_ownership_transferred(log: RawStateLog) -> MappedStateEvent:
    return MappedStateEvent(
        event_kind=MappedEventKind.OWNERSHIP_TRANSFERRED,
        contract_address=log.contract_address.lower(),
        metadata={
            "previous_owner": _topic_address(log.topics[1]),
            "new_owner": _topic_address(log.topics[2]),
        },
    )


def _map_role_event(log: RawStateLog, kind: MappedEventKind) -> MappedStateEvent:
    return MappedStateEvent(
        event_kind=kind,
        contract_address=log.contract_address.lower(),
        metadata={
            "role": log.topics[1].lower(),
            "account": _topic_address(log.topics[2]),
            "sender": _topic_address(log.topics[3]) if len(log.topics) > 3 else None,
        },
    )


def _topic_address(topic: str) -> str:
    normalized = topic.lower().removeprefix("0x")
    return "0x" + normalized[-40:]


def _uint_from_data(data: bytes) -> int:
    if not data:
        return 0
    return int.from_bytes(data[-32:], byteorder="big")
