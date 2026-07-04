"""M4 honeypot trade-path simulation state schema."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.models.enums import HoneypotSimulationStatus


class HoneypotTradePathResult(BaseModel):
    """Single phase of buy / transfer / sell — populated in M4.1+."""

    attempted: bool = False
    success: bool | None = None
    tax_bps: int | None = None
    revert_reason: str | None = None
    gas_used: int | None = None


class HoneypotSimulationState(BaseModel):
    """M4 schema shell — all paths NOT_RUN until M4.1."""

    status: HoneypotSimulationStatus = HoneypotSimulationStatus.NOT_RUN
    fork_block: int | None = None
    pair_address: str | None = None
    router_address: str | None = None
    buy: HoneypotTradePathResult = Field(default_factory=HoneypotTradePathResult)
    transfer: HoneypotTradePathResult = Field(default_factory=HoneypotTradePathResult)
    sell: HoneypotTradePathResult = Field(default_factory=HoneypotTradePathResult)
    round_trip_success: bool | None = None


def build_not_run_simulation_state() -> HoneypotSimulationState:
    """Return the default M4.0 simulation snapshot."""
    return HoneypotSimulationState(status=HoneypotSimulationStatus.NOT_RUN)
