"""Shared test helpers."""

TEST_CHAIN_ID = 11155111


def scan_create_payload(
    scan_type: str,
    target_address: str,
    *,
    chain_id: int = TEST_CHAIN_ID,
) -> dict[str, object]:
    return {
        "scan_type": scan_type,
        "target_address": target_address,
        "chain_id": chain_id,
    }
