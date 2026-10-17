"""Metric observations through the agent's existing tool contracts."""

from src.tools.registry import Tool, ToolRegistry

from simulation.engine import ReplayEngine


def register_metric_tools(registry: ToolRegistry, engine: ReplayEngine) -> None:
    contracts = [
        ("get_server_metrics", "Read server metric samples through the current virtual minute.",
         "server_id", engine.metrics),
        ("get_service_network_metrics", "Read peer network metrics through the current virtual minute.",
         "service", engine.network_peers),
    ]
    if callable(getattr(engine, "database_metrics", None)):
        contracts.append(("get_database_metrics",
                          "Read database connection-pool samples through the current virtual minute.",
                          "database_id", engine.database_metrics))
    for name, description, field, handler in contracts:
        registry.register(Tool(name, description,
                               {"type": "object", "properties": {field: {"type": "string"}},
                                "required": [field], "additionalProperties": False}, handler))
