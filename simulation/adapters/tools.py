"""Connect replay observations to the existing tool registry and permissions."""

from src.tools.executor import ToolExecutor
from src.tools.registry import ToolRegistry

from simulation.adapters.incidents_api import register_incident_tools
from simulation.adapters.logs_api import register_log_tools
from simulation.adapters.metrics_api import register_metric_tools
from simulation.engine import ReplayEngine
from simulation.scenario_loader import PUBLIC_TOOL_NAMES


TOOL_NAMES = PUBLIC_TOOL_NAMES


def replay_tools(engine: ReplayEngine, allowed: frozenset[str] | None = None) -> ToolExecutor:
    registry = ToolRegistry()
    register_incident_tools(registry, engine)
    register_metric_tools(registry, engine)
    register_log_tools(registry, engine)
    permitted = engine.scenario.allowed_tools
    return ToolExecutor(registry, permitted if allowed is None else permitted & frozenset(allowed))
