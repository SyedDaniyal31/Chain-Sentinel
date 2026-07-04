"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the ChainSentinel API."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = Field(default="ChainSentinel API", alias="APP_NAME")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development",
        alias="APP_ENV",
    )
    app_debug: bool = Field(default=False, alias="APP_DEBUG")
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_secret_key: str = Field(default="change-me", alias="API_SECRET_KEY")
    cors_origins: list[str] = Field(
        default=["http://localhost:3000"],
        alias="CORS_ORIGINS",
    )
    database_url: str = Field(
        default="postgresql+asyncpg://chainsentinel:chainsentinel_dev@localhost:5432/chainsentinel",
        alias="DATABASE_URL",
    )
    db_pool_size: int = Field(default=5, alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=10, alias="DB_MAX_OVERFLOW")
    db_auto_create_tables: bool = Field(
        default=True,
        alias="DB_AUTO_CREATE_TABLES",
        description="Create tables on startup (development only; use Alembic in production).",
    )
    eth_rpc_url: str = Field(
        default="https://ethereum-rpc.publicnode.com",
        alias="ETH_RPC_URL",
        description="JSON-RPC override for the primary chain (CHAIN_ID).",
    )
    eth_rpc_timeout_seconds: int = Field(
        default=30,
        alias="ETH_RPC_TIMEOUT_SECONDS",
        description="HTTP timeout for outbound JSON-RPC requests.",
    )
    chain_id: int | None = Field(
        default=1,
        alias="CHAIN_ID",
        description="Primary chain ID for RPC URL override via ETH_RPC_URL.",
    )
    etherscan_api_key: str | None = Field(
        default=None,
        alias="ETHERSCAN_API_KEY",
        description="Optional Etherscan API key for verified source capability analysis.",
    )
    trade_simulation_enabled: bool = Field(
        default=False,
        alias="TRADE_SIMULATION_ENABLED",
        description="Enable Anvil fork trade simulation (Rug Pull Detector V3).",
    )
    anvil_rpc_url: str = Field(
        default="http://127.0.0.1:8545",
        alias="ANVIL_RPC_URL",
        description="JSON-RPC URL for Anvil used during trade simulation.",
    )
    fork_rpc_url: str | None = Field(
        default=None,
        alias="FORK_RPC_URL",
        description="Upstream RPC to fork (defaults to ETH_RPC_URL when unset).",
    )
    simulation_fork_block_number: int | None = Field(
        default=None,
        alias="SIMULATION_FORK_BLOCK_NUMBER",
        description="Optional pinned block for reproducible fork simulations.",
    )
    simulation_eth_amount_wei: int = Field(
        default=10**17,
        alias="SIMULATION_ETH_AMOUNT_WEI",
        description="ETH amount used for simulated DEX buys (default 0.1 ETH).",
    )
    anvil_auto_start: bool = Field(
        default=False,
        alias="ANVIL_AUTO_START",
        description="Spawn a local Anvil fork process when trade simulation is enabled.",
    )
    anvil_binary: str = Field(
        default="anvil",
        alias="ANVIL_BINARY",
        description="Path to the Foundry Anvil binary.",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance (one per process)."""
    return Settings()
