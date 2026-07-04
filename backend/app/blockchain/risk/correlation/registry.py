"""Correlation rule registry (M7.2)."""

from __future__ import annotations

from app.blockchain.risk.correlation.rule import CorrelationRuleHandler


class DuplicateCorrelationRuleError(ValueError):
    """Raised when registering a correlation rule with an existing identifier."""


class CorrelationRuleRegistry:
    """Registry for correlation rule handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, CorrelationRuleHandler] = {}

    def register(self, handler: CorrelationRuleHandler) -> None:
        rule_id = handler.definition.id
        if rule_id in self._handlers:
            raise DuplicateCorrelationRuleError(f"Correlation rule already registered: {rule_id}")
        self._handlers[rule_id] = handler

    def get(self, rule_id: str) -> CorrelationRuleHandler | None:
        return self._handlers.get(rule_id)

    def all_handlers(self) -> tuple[CorrelationRuleHandler, ...]:
        return tuple(
            sorted(
                self._handlers.values(),
                key=lambda handler: (handler.definition.priority, handler.definition.id),
            )
        )

    def clear(self) -> None:
        self._handlers.clear()

    def __len__(self) -> int:
        return len(self._handlers)


_default_registry: CorrelationRuleRegistry | None = None


def get_default_registry() -> CorrelationRuleRegistry:
    """Return the process-wide registry populated with built-in correlation rules."""
    global _default_registry
    if _default_registry is None:
        from app.blockchain.risk.correlation.builtin_rules import register_builtin_rules

        _default_registry = CorrelationRuleRegistry()
        register_builtin_rules(_default_registry)
    return _default_registry
