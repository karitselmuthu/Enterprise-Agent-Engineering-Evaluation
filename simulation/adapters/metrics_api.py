"""Metric observations through the agent's existing tool contracts."""

from src.tools.registry import Tool, ToolRegistry

from simulation.engine import ReplayEngine


def register_metric_tools(registry: ToolRegistry, engine: ReplayEngine) -> None:
    for name, description, field, handler in (
        ("get_server_metrics", "Read server metric samples through the current virtual minute.",
         "server_id", engine.metrics),
        ("get_service_network_metrics", "Read peer network metrics through the current virtual minute.",
         "service", engine.network_peers),
    ):
        registry.register(Tool(name, description,
                               {"type": "object", "properties": {field: {"type": "string"}},
                                "required": [field], "additionalProperties": False}, handler))
