"""Runtime control modules for AgentTelemetry.

Transforms passive observability into active runtime control by using
the agent span taxonomy for real-time decision-making.
"""

from agenttelemetry.runtime.circuit_breaker import (
    AgentCircuitBreaker,
    BreakerPolicy,
    BreakerAction,
    CircuitBreakerProcessor,
)

__all__ = [
    "AgentCircuitBreaker",
    "BreakerPolicy",
    "BreakerAction",
    "CircuitBreakerProcessor",
]
