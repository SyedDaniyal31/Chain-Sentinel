"""Chain catalog business logic (M5.0)."""

from app.blockchain.chain_registry import ChainRegistry, get_chain_registry
from app.schemas.chain import ChainListResponse, ChainResponse


class ChainService:
    """Read-only access to supported chain metadata."""

    def __init__(self, registry: ChainRegistry | None = None) -> None:
        self._registry = registry or get_chain_registry()

    def list_supported_chains(self) -> ChainListResponse:
        chains = [
            ChainResponse(
                chain_id=chain.chain_id,
                name=chain.display_name,
                native_currency=chain.native_currency,
                explorer_url=chain.explorer_url,
                testnet=chain.testnet,
                supported=chain.supported,
            )
            for chain in self._registry.list_supported()
        ]
        return ChainListResponse(chains=chains)
