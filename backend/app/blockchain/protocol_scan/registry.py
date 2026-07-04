"""Discovery provider registry (M8.1)."""

from __future__ import annotations

from app.blockchain.protocol_scan.provider import ProtocolDiscoveryProvider


class DuplicateDiscoveryProviderError(ValueError):
    """Raised when registering a provider with an existing name."""


class DiscoveryProviderRegistry:
    """Registry for pluggable protocol discovery providers."""

    DEFAULT_PROVIDER = "on_chain"

    def __init__(self) -> None:
        self._providers: dict[str, ProtocolDiscoveryProvider] = {}

    def register(self, name: str, provider: ProtocolDiscoveryProvider) -> None:
        if name in self._providers:
            raise DuplicateDiscoveryProviderError(f"Discovery provider already registered: {name}")
        self._providers[name] = provider

    def get(self, name: str) -> ProtocolDiscoveryProvider | None:
        return self._providers.get(name)

    def require(self, name: str) -> ProtocolDiscoveryProvider:
        provider = self.get(name)
        if provider is None:
            raise KeyError(f"Discovery provider not registered: {name}")
        return provider

    def all_names(self) -> tuple[str, ...]:
        return tuple(sorted(self._providers))

    def __len__(self) -> int:
        return len(self._providers)
