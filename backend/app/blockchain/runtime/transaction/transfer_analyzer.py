"""Token and native transfer detection (M9.1)."""

from __future__ import annotations

from app.blockchain.runtime.transaction.models import (
    DecodedFunction,
    TokenStandard,
    TokenTransfer,
    TransactionMetadata,
)


class TransferAnalyzer:
    """Detect ETH, ERC20, ERC721, and ERC1155 transfers from runtime transactions."""

    ERC20_TRANSFER = "a9059cbb"
    ERC20_TRANSFER_FROM = "23b872dd"
    ERC721_SAFE_TRANSFER_FROM = "42842e0e"
    ERC721_SAFE_TRANSFER_FROM_DATA = "b88d4fde"
    ERC1155_SAFE_TRANSFER_FROM = "f242432a"
    ERC1155_SAFE_BATCH_TRANSFER_FROM = "2eb2c2d6"

    @classmethod
    def analyze(
        cls,
        metadata: TransactionMetadata,
        decoded_function: DecodedFunction | None,
    ) -> tuple[TokenTransfer, ...]:
        transfers: list[TokenTransfer] = []

        if metadata.value_wei > 0:
            recipient = metadata.to_address or metadata.from_address
            transfers.append(
                TokenTransfer(
                    standard=TokenStandard.NATIVE,
                    from_address=metadata.from_address,
                    to_address=recipient,
                    amount=metadata.value_wei,
                    token_address=None,
                )
            )

        if decoded_function is None:
            return tuple(transfers)

        selector = decoded_function.selector
        token_address = metadata.to_address

        if selector == cls.ERC20_TRANSFER and decoded_function.arguments:
            recipient = str(decoded_function.arguments[0].value)
            amount = _coerce_int(decoded_function.arguments[1].value)
            transfers.append(
                TokenTransfer(
                    standard=TokenStandard.ERC20,
                    from_address=metadata.from_address,
                    to_address=recipient,
                    amount=amount,
                    token_address=token_address,
                )
            )
        elif selector == cls.ERC20_TRANSFER_FROM and len(decoded_function.arguments) >= 3:
            sender = str(decoded_function.arguments[0].value)
            recipient = str(decoded_function.arguments[1].value)
            amount = _coerce_int(decoded_function.arguments[2].value)
            transfers.append(
                TokenTransfer(
                    standard=TokenStandard.ERC20,
                    from_address=sender,
                    to_address=recipient,
                    amount=amount,
                    token_address=token_address,
                    operator=metadata.from_address,
                )
            )
        elif selector in {cls.ERC721_SAFE_TRANSFER_FROM, cls.ERC721_SAFE_TRANSFER_FROM_DATA}:
            sender = str(decoded_function.arguments[0].value)
            recipient = str(decoded_function.arguments[1].value)
            token_id = _coerce_int(decoded_function.arguments[2].value)
            transfers.append(
                TokenTransfer(
                    standard=TokenStandard.ERC721,
                    from_address=sender,
                    to_address=recipient,
                    amount=None,
                    token_address=token_address,
                    token_id=token_id,
                    operator=metadata.from_address,
                )
            )
        elif selector == cls.ERC1155_SAFE_TRANSFER_FROM and len(decoded_function.arguments) >= 4:
            sender = str(decoded_function.arguments[0].value)
            recipient = str(decoded_function.arguments[1].value)
            token_id = _coerce_int(decoded_function.arguments[2].value)
            amount = _coerce_int(decoded_function.arguments[3].value)
            transfers.append(
                TokenTransfer(
                    standard=TokenStandard.ERC1155,
                    from_address=sender,
                    to_address=recipient,
                    amount=amount,
                    token_address=token_address,
                    token_id=token_id,
                    operator=metadata.from_address,
                )
            )
        elif selector == cls.ERC1155_SAFE_BATCH_TRANSFER_FROM and len(decoded_function.arguments) >= 4:
            sender = str(decoded_function.arguments[0].value)
            recipient = str(decoded_function.arguments[1].value)
            token_ids = decoded_function.arguments[2].value
            amounts = decoded_function.arguments[3].value
            if isinstance(token_ids, tuple) and isinstance(amounts, tuple):
                for token_id, amount in zip(token_ids, amounts, strict=False):
                    transfers.append(
                        TokenTransfer(
                            standard=TokenStandard.ERC1155,
                            from_address=sender,
                            to_address=recipient,
                            amount=_coerce_int(amount),
                            token_address=token_address,
                            token_id=_coerce_int(token_id),
                            operator=metadata.from_address,
                        )
                    )

        return tuple(transfers)


def _coerce_int(value: object) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.startswith("0x"):
        return int(value, 16)
    return int(value)
