"""Attack scenario execution helpers (M9.4)."""

from __future__ import annotations

from app.blockchain.runtime.simulation.attack_library import ATTACK_LIBRARY
from app.blockchain.runtime.simulation.models import AttackScenario, AttackType, SimulationResult
from app.blockchain.runtime.simulation.simulation_engine import SimulationEngine


class AttackExecutor:
    """Execute reusable attack scenarios through the simulation engine."""

    def __init__(self, engine: SimulationEngine | None = None) -> None:
        self._engine = engine or SimulationEngine()

    async def execute(self, attack: AttackScenario) -> tuple[SimulationResult, ...]:
        return await self._engine.simulate_attack(attack)

    async def execute_by_type(self, attack_type: AttackType) -> tuple[SimulationResult, ...]:
        attack = ATTACK_LIBRARY.get(attack_type)
        if attack is None:
            raise ValueError(f"unknown attack type: {attack_type.value}")
        return await self.execute(attack)
