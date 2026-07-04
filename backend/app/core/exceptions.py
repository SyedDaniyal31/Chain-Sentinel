"""Application-specific exceptions."""


class ScanNotFoundError(Exception):
    """Raised when a scan job ID does not exist."""

    def __init__(self, scan_id: int) -> None:
        self.scan_id = scan_id
        super().__init__(f"Scan job {scan_id} not found")


class BlockchainRpcError(Exception):
    """Raised when JSON-RPC connectivity or chain validation fails."""

    def __init__(self, message: str) -> None:
        self.message = message
        super().__init__(message)


class UnsupportedChainError(Exception):
    """Raised when a chain_id is not registered or not supported."""

    def __init__(self, chain_id: int) -> None:
        self.chain_id = chain_id
        super().__init__(f"Unsupported chain_id: {chain_id}")
