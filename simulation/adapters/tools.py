"""Connect replay observations to the existing tool registry and permissions."""

from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry

from simulation.adapters.incidents_api import register_incident_tools
from simulation.adapters.logs_api import register_log_tools
from simulation.adapters.metrics_api import register_metric_tools
from simulation.engine import ReplayEngine
from simulation.scenario_loader import PUBLIC_TOOL_NAMES


TOOL_NAMES = PUBLIC_TOOL_NAMES


def contract_tools(backend: object, permitted: frozenset[str]) -> ToolExecutor:
    """Register the shared contracts around any observation backend."""
    registry = ToolRegistry()
    register_incident_tools(registry, backend)
    register_metric_tools(registry, backend)
    register_log_tools(registry, backend)
    return ToolExecutor(registry, permitted)


def replay_tools(engine: ReplayEngine, allowed: frozenset[str] | None = None) -> ToolExecutor:
    permitted = engine.scenario.allowed_tools
    return contract_tools(engine, permitted if allowed is None else permitted & frozenset(allowed))
