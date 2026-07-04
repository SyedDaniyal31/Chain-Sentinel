"""EVM encoding helpers for Uniswap V2 and ERC-20 trade simulation."""

from eth_abi import encode

# keccak256("getPair(address,address)")[:4]
GET_PAIR_SELECTOR = bytes.fromhex("e6a43905")
# keccak256("getAmountsOut(uint256,address[])")[:4]
GET_AMOUNTS_OUT_SELECTOR = bytes.fromhex("d06ca61f")
# keccak256("balanceOf(address)")[:4]
BALANCE_OF_SELECTOR = bytes.fromhex("70a08231")
# keccak256("approve(address,uint256)")[:4]
APPROVE_SELECTOR = bytes.fromhex("095ea7b3")
# keccak256("transfer(address,uint256)")[:4]
TRANSFER_SELECTOR = bytes.fromhex("a9059cbb")
# swapExactETHForTokensSupportingFeeOnTransferTokens(uint256,address[],address,uint256)
SWAP_ETH_FOR_TOKENS_SELECTOR = bytes.fromhex("b6f9de95")
# swapExactTokensForETHSupportingFeeOnTransferTokens(uint256,uint256,address[],address,uint256)
SWAP_TOKENS_FOR_ETH_SELECTOR = bytes.fromhex("791ac947")

MAX_UINT256 = (1 << 256) - 1
DEFAULT_SIMULATION_DEADLINE_OFFSET = 600


def encode_get_pair(token_a: str, token_b: str) -> str:
    args = encode(["address", "address"], [_checksum(token_a), _checksum(token_b)])
    return "0x" + GET_PAIR_SELECTOR.hex() + args.hex()


def encode_get_amounts_out(amount_in: int, path: list[str]) -> str:
    args = encode(["uint256", "address[]"], [amount_in, [_checksum(addr) for addr in path]])
    return "0x" + GET_AMOUNTS_OUT_SELECTOR.hex() + args.hex()


def encode_balance_of(holder: str) -> str:
    args = encode(["address"], [_checksum(holder)])
    return "0x" + BALANCE_OF_SELECTOR.hex() + args.hex()


def encode_approve(spender: str, amount: int) -> str:
    args = encode(["address", "uint256"], [_checksum(spender), amount])
    return "0x" + APPROVE_SELECTOR.hex() + args.hex()


def encode_transfer(recipient: str, amount: int) -> str:
    args = encode(["address", "uint256"], [_checksum(recipient), amount])
    return "0x" + TRANSFER_SELECTOR.hex() + args.hex()


def encode_swap_eth_for_tokens(
    amount_out_min: int,
    path: list[str],
    recipient: str,
    deadline: int,
) -> str:
    args = encode(
        ["uint256", "address[]", "address", "uint256"],
        [amount_out_min, [_checksum(addr) for addr in path], _checksum(recipient), deadline],
    )
    return "0x" + SWAP_ETH_FOR_TOKENS_SELECTOR.hex() + args.hex()


def encode_swap_tokens_for_eth(
    amount_in: int,
    amount_out_min: int,
    path: list[str],
    recipient: str,
    deadline: int,
) -> str:
    args = encode(
        ["uint256", "uint256", "address[]", "address", "uint256"],
        [
            amount_in,
            amount_out_min,
            [_checksum(addr) for addr in path],
            _checksum(recipient),
            deadline,
        ],
    )
    return "0x" + SWAP_TOKENS_FOR_ETH_SELECTOR.hex() + args.hex()


def decode_address(return_data: bytes) -> str | None:
    if len(return_data) < 32:
        return None
    address_bytes = return_data[-20:]
    if address_bytes == b"\x00" * 20:
        return None
    return "0x" + address_bytes.hex()


def decode_uint256(return_data: bytes) -> int:
    if len(return_data) < 32:
        return 0
    return int.from_bytes(return_data[-32:], byteorder="big")


def decode_amounts_out(return_data: bytes) -> list[int]:
    if len(return_data) < 64:
        return []
    offset = int.from_bytes(return_data[0:32], byteorder="big")
    base = offset
    if base + 32 > len(return_data):
        return []
    length = int.from_bytes(return_data[base : base + 32], byteorder="big")
    amounts: list[int] = []
    for index in range(length):
        start = base + 32 + (index * 32)
        end = start + 32
        if end > len(return_data):
            break
        amounts.append(int.from_bytes(return_data[start:end], byteorder="big"))
    return amounts


def compute_tax_bps(expected_amount: int, actual_amount: int) -> int | None:
    """Return fee in basis points when actual delivery is below the quote."""
    if expected_amount <= 0:
        return None
    if actual_amount >= expected_amount:
        return 0
    lost = expected_amount - actual_amount
    return min(int((lost * 10_000) / expected_amount), 10_000)


def _checksum(address: str) -> str:
    from web3 import Web3

    return Web3.to_checksum_address(address)
