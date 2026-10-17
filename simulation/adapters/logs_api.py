"""Application and pod event observations through existing tool contracts."""

from src.tools.registry import Tool, ToolRegistry

from simulation.engine import ReplayEngine


def register_log_tools(registry: ToolRegistry, engine: ReplayEngine) -> None:
    for name, description, field, handler in (
        ("get_application_logs", "Read application logs through the current virtual minute.",
         "service", engine.logs),
        ("get_pod_events", "Read Kubernetes pod events through the current virtual minute.",
         "pod", engine.pod_events),
    ):
        registry.register(Tool(name, description,
                               {"type": "object", "properties": {field: {"type": "string"}},
                                "required": [field], "additionalProperties": False}, handler))
