"""Scan API request and response schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.blockchain.chain_registry import DEFAULT_CHAIN_ID
from app.core.validators import normalize_eth_address
from app.models.enums import RiskLevel, ScanJobStatus, ScanType
from app.schemas.scan_result import ScanResultResponse


class ScanCreateRequest(BaseModel):
    """Payload for initiating a new scan job."""

    scan_type: ScanType = Field(
        ...,
        examples=[ScanType.WALLET, ScanType.CONTRACT],
        description="Type of security analysis to perform.",
    )
    target_address: str = Field(
        ...,
        examples=["0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0"],
        description="EVM address to scan (checksummed or lowercase).",
    )
    chain_id: int = Field(
        default=DEFAULT_CHAIN_ID,
        ge=1,
        examples=[1, 11155111, 8453],
        description="EIP-155 chain ID to scan against (defaults to Ethereum Mainnet).",
    )

    @field_validator("target_address")
    @classmethod
    def validate_target_address(cls, value: str) -> str:
        return normalize_eth_address(value)

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "scan_type": "wallet",
                    "target_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb0",
                },
                {
                    "scan_type": "contract",
                    "target_address": "0xa231aa3388416ebc1b8f8a51b412327832524ca4",
                },
            ]
        }
    )


class ScanCreateResponse(BaseModel):
    """Minimal response after a scan job is queued."""

    id: int = Field(..., examples=[1], description="Database identifier for the scan job.")
    status: ScanJobStatus = Field(
        ...,
        examples=[ScanJobStatus.PENDING],
        description="Current job status.",
    )

    model_config = {
        "json_schema_extra": {
            "examples": [{"id": 1, "status": "pending"}]
        }
    }


class ScanJobResponse(BaseModel):
    """Complete scan job representation returned by GET /api/v1/scans/{id}."""

    id: int = Field(..., examples=[1], description="Database identifier for the scan job.")
    scan_type: ScanType = Field(..., examples=[ScanType.WALLET, ScanType.CONTRACT])
    target_address: str = Field(
        ...,
        examples=[
            "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
            "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
        ],
    )
    status: ScanJobStatus = Field(..., examples=[ScanJobStatus.PENDING])
    risk_score: Decimal | None = Field(
        None,
        examples=[None, Decimal("0.00"), Decimal("100.00")],
        description="Composite risk score 0.00–100.00; rule-based for contracts, mock for wallets until V2.",
    )
    created_at: datetime = Field(..., description="UTC timestamp when the job was created.")
    updated_at: datetime = Field(..., description="UTC timestamp when the job was last updated.")
    chain_id: int | None = Field(
        None,
        examples=[1, 11155111],
        description="EIP-155 chain ID captured from RPC when the scan executed.",
    )
    block_number: int | None = Field(
        None,
        examples=[21000000],
        description="Latest block height captured from RPC when the scan executed.",
    )
    rpc_endpoint: str | None = Field(
        None,
        examples=["https://ethereum-rpc.publicnode.com"],
        description="JSON-RPC endpoint used for this scan job.",
    )
    result: ScanResultResponse | None = Field(
        None,
        description="Analyzer output populated when scan completes (wallet or contract fields vary by scan_type).",
    )

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "id": 1,
                    "scan_type": "wallet",
                    "target_address": "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
                    "status": "completed",
                    "risk_score": "42.15",
                    "created_at": "2026-06-13T12:00:00+00:00",
                    "updated_at": "2026-06-13T12:00:05+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345678,
                        "wallet_balance_wei": 1000000000000000000,
                        "wallet_balance_eth": "1",
                        "is_contract": None,
                        "bytecode_size": None,
                        "created_at": "2026-06-13T12:00:05+00:00",
                    },
                },
                {
                    "id": 2,
                    "scan_type": "contract",
                    "target_address": "0x1f9840a85d5af5bf1d1762f925bdaddc4201f984",
                    "status": "completed",
                    "risk_score": "0.00",
                    "created_at": "2026-06-13T12:10:00+00:00",
                    "updated_at": "2026-06-13T12:10:04+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345680,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 24576,
                        "is_upgradeable": False,
                        "implementation_address": None,
                        "admin_address": None,
                        "admin_type": None,
                        "risk_score": "0.00",
                        "risk_level": "low",
                        "risk_reasons": ["No upgradeability indicators detected"],
                        "created_at": "2026-06-13T12:10:04+00:00",
                    },
                },
                {
                    "id": 3,
                    "scan_type": "contract",
                    "target_address": "0xa231aa3388416ebc1b8f8a51b412327832524ca4",
                    "status": "completed",
                    "risk_score": "100.00",
                    "created_at": "2026-06-13T12:20:00+00:00",
                    "updated_at": "2026-06-13T12:20:06+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345690,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 2048,
                        "is_upgradeable": True,
                        "implementation_address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                        "admin_address": "0x1234567890123456789012345678901234567890",
                        "admin_type": "eoa",
                        "risk_score": "100.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Contract uses an upgradeable EIP-1967 proxy pattern",
                            "Implementation contract address is exposed via storage slot",
                            "Upgrade admin is an externally owned account (elevated single-key upgrade risk)",
                        ],
                        "created_at": "2026-06-13T12:20:06+00:00",
                    },
                },
                {
                    "id": 4,
                    "scan_type": "contract",
                    "target_address": "0xb123456789012345678901234567890123456789",
                    "status": "completed",
                    "risk_score": "80.00",
                    "created_at": "2026-06-13T12:30:00+00:00",
                    "updated_at": "2026-06-13T12:30:05+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345700,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 2048,
                        "is_upgradeable": True,
                        "implementation_address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                        "admin_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                        "admin_type": "multisig",
                        "risk_score": "80.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Contract uses an upgradeable EIP-1967 proxy pattern",
                            "Implementation contract address is exposed via storage slot",
                            "Upgrade admin appears to be a Gnosis Safe-style multisig",
                        ],
                        "created_at": "2026-06-13T12:30:05+00:00",
                    },
                },
                {
                    "id": 5,
                    "scan_type": "contract",
                    "target_address": "0xc123456789012345678901234567890123456789",
                    "status": "completed",
                    "risk_score": "100.00",
                    "created_at": "2026-06-13T12:40:00+00:00",
                    "updated_at": "2026-06-13T12:40:06+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345710,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 2048,
                        "is_upgradeable": True,
                        "implementation_address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                        "admin_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                        "admin_type": "contract",
                        "owner_address": "0x1234567890123456789012345678901234567890",
                        "owner_type": "eoa",
                        "risk_score": "100.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Contract uses an upgradeable EIP-1967 proxy pattern",
                            "Implementation contract address is exposed via storage slot",
                            "Upgrade admin is an externally owned account (elevated single-key upgrade risk)",
                            "ProxyAdmin owner() traced to controlling address",
                        ],
                        "created_at": "2026-06-13T12:40:06+00:00",
                    },
                },
                {
                    "id": 6,
                    "scan_type": "contract",
                    "target_address": "0xd123456789012345678901234567890123456789",
                    "status": "completed",
                    "risk_score": "77.00",
                    "created_at": "2026-06-13T12:50:00+00:00",
                    "updated_at": "2026-06-13T12:50:06+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345720,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 2048,
                        "is_upgradeable": True,
                        "implementation_address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                        "admin_address": "0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
                        "admin_type": "contract",
                        "owner_address": "0xcccccccccccccccccccccccccccccccccccccccc",
                        "owner_type": "contract",
                        "is_timelock": True,
                        "min_delay": 86400,
                        "risk_score": "77.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Contract uses an upgradeable EIP-1967 proxy pattern",
                            "Implementation contract address is exposed via storage slot",
                            "Upgrade authority protected by TimelockController (min delay 86400s)",
                            "ProxyAdmin owner() traced to controlling address",
                        ],
                        "created_at": "2026-06-13T12:50:06+00:00",
                    },
                },
                {
                    "id": 7,
                    "scan_type": "contract",
                    "target_address": "0xe123456789012345678901234567890123456789",
                    "status": "completed",
                    "risk_score": "100.00",
                    "created_at": "2026-06-13T13:00:00+00:00",
                    "updated_at": "2026-06-13T13:00:06+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345730,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 8192,
                        "is_upgradeable": True,
                        "implementation_address": "0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef",
                        "admin_address": "0x1234567890123456789012345678901234567890",
                        "admin_type": "eoa",
                        "mint_capability": True,
                        "pause_capability": True,
                        "blacklist_capability": True,
                        "ownership_capability": True,
                        "risk_score": "100.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Contract uses an upgradeable EIP-1967 proxy pattern",
                            "Implementation contract address is exposed via storage slot",
                            "Upgrade admin is an externally owned account (elevated single-key upgrade risk)",
                            "Contract exposes mint capability (supply inflation risk)",
                            "Contract exposes pause capability (user funds may be frozen)",
                            "Contract exposes blacklist capability (selective transfer blocking)",
                            "Contract exposes centralized ownership controls (transferOwnership)",
                        ],
                        "created_at": "2026-06-13T13:00:06+00:00",
                    },
                },
                {
                    "id": 8,
                    "scan_type": "contract",
                    "target_address": "0xf123456789012345678901234567890123456789",
                    "status": "completed",
                    "risk_score": "100.00",
                    "created_at": "2026-06-13T13:10:00+00:00",
                    "updated_at": "2026-06-13T13:10:06+00:00",
                    "result": {
                        "chain_id": 11155111,
                        "latest_block": 12345740,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 6144,
                        "is_upgradeable": False,
                        "implementation_address": None,
                        "admin_address": None,
                        "admin_type": None,
                        "trading_enabled_control": True,
                        "whitelist_control": True,
                        "blacklist_sell_blocking": True,
                        "transfer_tax_control": True,
                        "risk_score": "100.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Contract exposes trading launch controls (enableTrading / openTrading)",
                            "Contract exposes whitelist controls (selective trading gate)",
                            "Contract exposes blacklist and sell-restriction patterns (honeypot risk)",
                            "Contract exposes configurable transfer tax / fee controls",
                        ],
                        "created_at": "2026-06-13T13:10:06+00:00",
                    },
                },
                {
                    "id": 9,
                    "scan_type": "contract",
                    "target_address": "0x0123456789012345678901234567890123456789",
                    "status": "completed",
                    "risk_score": "100.00",
                    "created_at": "2026-06-13T13:20:00+00:00",
                    "updated_at": "2026-06-13T13:20:12+00:00",
                    "result": {
                        "chain_id": 1,
                        "latest_block": 21234567,
                        "wallet_balance_wei": None,
                        "wallet_balance_eth": None,
                        "is_contract": True,
                        "bytecode_size": 4096,
                        "is_upgradeable": False,
                        "implementation_address": None,
                        "trade_simulated": True,
                        "can_buy": True,
                        "can_sell": False,
                        "buy_tax_bps": 500,
                        "sell_tax_bps": 9900,
                        "blacklist_sell_blocking": True,
                        "transfer_tax_control": True,
                        "risk_score": "100.00",
                        "risk_level": "high",
                        "risk_reasons": [
                            "Trade simulation confirmed sell path reverts (honeypot)",
                            "Trade simulation measured elevated sell tax (9900 bps)",
                        ],
                        "created_at": "2026-06-13T13:20:12+00:00",
                    },
                },
            ]
        },
    )


class ScanListItemResponse(BaseModel):
    """Compact scan row for paginated history listings."""

    id: int = Field(..., examples=[42])
    scan_type: ScanType = Field(..., examples=[ScanType.CONTRACT])
    target_address: str = Field(
        ...,
        examples=["0x742d35cc6634c0532925a3b844bc9e7595f0beb0"],
    )
    status: ScanJobStatus = Field(..., examples=[ScanJobStatus.COMPLETED])
    risk_score: Decimal | None = Field(None, examples=[Decimal("77.00")])
    risk_level: RiskLevel | None = Field(None, examples=[RiskLevel.HIGH])
    created_at: datetime = Field(..., examples=["2026-06-13T12:00:00+00:00"])

    model_config = ConfigDict(from_attributes=True)


class PaginatedScanListResponse(BaseModel):
    """Paginated scan history response."""

    items: list[ScanListItemResponse] = Field(default_factory=list)
    total: int = Field(..., ge=0, examples=[125])
    page: int = Field(..., ge=1, examples=[1])
    page_size: int = Field(..., ge=1, examples=[20])
    total_pages: int = Field(..., ge=0, examples=[7])

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "items": [
                        {
                            "id": 42,
                            "scan_type": "contract",
                            "target_address": "0x742d35cc6634c0532925a3b844bc9e7595f0beb0",
                            "status": "completed",
                            "risk_score": "77.00",
                            "risk_level": "high",
                            "created_at": "2026-06-13T12:00:00+00:00",
                        }
                    ],
                    "total": 125,
                    "page": 1,
                    "page_size": 20,
                    "total_pages": 7,
                }
            ]
        }
    )


class ScanSummaryResponse(BaseModel):
    """Aggregate scan intelligence metrics."""

    total_scans: int = Field(..., ge=0, examples=[125])
    completed_scans: int = Field(..., ge=0, examples=[110])
    failed_scans: int = Field(..., ge=0, examples=[15])
    high_risk: int = Field(..., ge=0, examples=[25])
    medium_risk: int = Field(..., ge=0, examples=[45])
    low_risk: int = Field(..., ge=0, examples=[40])
    average_risk_score: float = Field(..., ge=0, examples=[58.7])

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "examples": [
                {
                    "total_scans": 125,
                    "completed_scans": 110,
                    "failed_scans": 15,
                    "high_risk": 25,
                    "medium_risk": 45,
                    "low_risk": 40,
                    "average_risk_score": 58.7,
                }
            ]
        },
    )

