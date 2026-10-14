"""Deterministic response builder."""
import re
from typing import Any
from src.tools.executor import ToolResult

class MockBackend:
    def select_tool(self, request: str, tools: list[dict[str, Any]]
                    ) -> tuple[str, dict[str, Any]] | None:
        incident = re.search(r"INC-\d+", request, re.IGNORECASE)
        if incident:
            return "get_incident", {"incident_id": incident.group().upper()}
        service = re.search(r"(?:status|health)\s+(?:of\s+)?(?:service\s+)?([\w-]+)", request, re.IGNORECASE)
        if service:
            return "get_service_status", {"service": service.group(1).lower()}
        return None

    def interpret(self, request: str, result: ToolResult) -> str:
        if not result.ok:
            return f"Investigation failed ({result.error_code}): {result.error}"
        data = result.content
        if result.name == "get_incident":
            return (f"Incident {data['id']}: {data['title']}. Impact: {data['impact']}. "
                    f"Suspected cause: {data['suspected_cause']}. "
                    f"Recommended action: {data['recommended_action']}.")
        if result.name == "get_service_status":
            return f"Service {data['service']} is {data['status']}."
        return str(data)
