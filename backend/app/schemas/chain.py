"""Chain catalog API schemas (M5.0)."""

from pydantic import BaseModel, ConfigDict, Field


class ChainResponse(BaseModel):
    """Public chain metadata exposed by GET /api/v1/chains."""

    chain_id: int = Field(..., examples=[1])
    name: str = Field(..., examples=["Ethereum Mainnet"])
    native_currency: str = Field(..., examples=["ETH"])
    explorer_url: str = Field(..., examples=["https://etherscan.io"])
    testnet: bool = Field(..., examples=[False])
    supported: bool = Field(..., examples=[True])

    model_config = ConfigDict(from_attributes=True)


class ChainListResponse(BaseModel):
    """Supported chain catalog."""

    chains: list[ChainResponse] = Field(default_factory=list)
