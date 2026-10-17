"""Incident observation through the agent's existing tool contract."""

from src.tools.registry import Tool, ToolRegistry

from simulation.engine import ReplayEngine


def register_incident_tools(registry: ToolRegistry, engine: ReplayEngine) -> None:
    registry.register(Tool(
        "get_incident_record", "Read the current incident alert.",
        {"type": "object", "properties": {"incident_id": {"type": "string"}},
         "required": ["incident_id"], "additionalProperties": False}, engine.incident))
