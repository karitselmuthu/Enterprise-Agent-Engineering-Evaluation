"""Connect replay observations to the existing tool registry and permissions."""

from src.tools.executor import ToolExecutor
from src.tools.registry import Tool, ToolRegistry

from simulation.engine import ReplayEngine
from simulation.scenario_loader import PUBLIC_TOOL_NAMES


TOOL_NAMES = PUBLIC_TOOL_NAMES


def replay_tools(engine: ReplayEngine, allowed: frozenset[str] | None = None) -> ToolExecutor:
    registry = ToolRegistry()
    for name, description, field, handler in (
        ("get_incident_record", "Read the current incident alert.", "incident_id", engine.incident),
        ("get_server_metrics", "Read server metric samples through the current virtual minute.",
         "server_id", engine.metrics),
        ("get_application_logs", "Read application logs through the current virtual minute.",
         "service", engine.logs),
    ):
        registry.register(Tool(name, description, {"type": "object",
            "properties": {field: {"type": "string"}}, "required": [field],
            "additionalProperties": False}, handler))
    return ToolExecutor(registry, engine.scenario.allowed_tools if allowed is None else allowed)
