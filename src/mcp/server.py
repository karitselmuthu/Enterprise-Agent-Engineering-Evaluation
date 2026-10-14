"""IT operations tools exposed over the official MCP Python SDK."""

from typing import TypedDict

from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError

from src.tools.mock_infrastructure import get_incident, get_service_status

mcp = MCPServer("enterprise-it-operations")

class IncidentRecord(TypedDict):
    id: str
    title: str
    impact: str
    suspected_cause: str
    recommended_action: str

class ServiceStatus(TypedDict):
    service: str
    status: str

@mcp.tool()
def incident_record(incident_id: str) -> IncidentRecord:
    """Read a local incident record by ID."""
    try:
        return get_incident(incident_id)
    except (FileNotFoundError, ValueError) as exc:
        raise ToolError(str(exc)) from exc


@mcp.tool()
def service_status(service: str) -> ServiceStatus:
    """Read the health of a named infrastructure service."""
    try:
        return get_service_status(service)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


if __name__ == "__main__":
    mcp.run(transport="stdio")
