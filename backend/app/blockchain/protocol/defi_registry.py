"""Known DeFi deployment registry for M6.1 protocol detection."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class DeFiDeployment:
    """Known on-chain deployment for a DeFi protocol component."""

    protocol: str
    role: str
    chain_id: int
    address: str


DEFI_DEPLOYMENTS: tuple[DeFiDeployment, ...] = (
    # Ethereum mainnet
    DeFiDeployment("Uniswap V2", "factory", 1, "0x5c69bee701ef814a2b6a3edd4b1652cb9cc5aa6f"),
    DeFiDeployment("Uniswap V2", "router", 1, "0x7a250d5630b4cf539739df2c5dacb4c659f2488d"),
    DeFiDeployment("Uniswap V3", "factory", 1, "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984"),
    DeFiDeployment("Uniswap V3", "router", 1, "0x68b3465833fb72a70ecd978e0e7a112bb5527bff"),
    DeFiDeployment("SushiSwap", "factory", 1, "0xc0aee478e3658e2610c5f7a4a2e1777ce9e4f2c"),
    DeFiDeployment("SushiSwap", "router", 1, "0xd9e1ce17f2641f24ae83637ab66a2cca9c378b9f"),
    DeFiDeployment("Curve", "router", 1, "0x99a58482c5f59cff7d9d248a6c415aff0a151b0b"),
    DeFiDeployment("Balancer", "vault", 1, "0xba12222222228d8ba445958a75a0704d566bf2c8"),
    DeFiDeployment("Aave", "pool", 1, "0x87870bca3f3fd6335c3f4ce8392d69350b4fa4e2"),
    DeFiDeployment("Compound", "comptroller", 1, "0x3d9819210a31b4961b5e55aaf6cf52de0a3b83b7"),
    DeFiDeployment("Spark", "pool", 1, "0xc13e21b648a5e7a66a55a667f3c8bff20087efa9"),
    DeFiDeployment("Morpho", "market", 1, "0xbbbbbbbbbb9cc5e90e3b3af64bdaf62c37eeffcb"),
    # BSC
    DeFiDeployment("PancakeSwap", "factory", 56, "0xcA143Ce32Fe78f1f7019d7d551a6402fC5350c73"),
    DeFiDeployment("PancakeSwap", "router", 56, "0x10ed43c718714eb63d5aa57b78b54704e256024e"),
    # Base
    DeFiDeployment("Aerodrome", "factory", 8453, "0x420dd381b31aef6683db6b902084cb0ffece40da"),
    DeFiDeployment("Aerodrome", "router", 8453, "0xcF77a3Ba9A5CA399B7c97c74d54e5b1Beb874E43"),
    # Sepolia (test fixtures)
    DeFiDeployment("Uniswap V2", "factory", 11155111, "0x7e0987e5b3a30e3f2828572cd659dd524b256b59"),
    DeFiDeployment("Uniswap V2", "router", 11155111, "0xc532a74256d3db42d0bb7b040438bed69799a8cc"),
)


STABLECOIN_NAME_MARKERS: tuple[str, ...] = (
    "USDC",
    "USDT",
    "DAI",
    "FRAX",
    "LUSD",
    "TUSD",
    "BUSD",
)


def match_deployments(chain_id: int, target_address: str) -> list[DeFiDeployment]:
    """Return registry deployments matching the target address on a chain."""
    normalized = target_address.lower()
    return [
        deployment
        for deployment in DEFI_DEPLOYMENTS
        if deployment.chain_id == chain_id and deployment.address.lower() == normalized
    ]


def source_contains_marker(source_code: str | None, markers: tuple[str, ...]) -> bool:
    if not source_code:
        return False
    upper = source_code.upper()
    return any(marker in upper for marker in markers)
