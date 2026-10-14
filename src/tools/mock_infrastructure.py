"""Fixture backed infrastructure tools."""
import json
from pathlib import Path
from .registry import Tool, ToolRegistry

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_incidents"

def get_incident(incident_id: str) -> dict:
    if not incident_id or not all(c.isalnum() or c in "-_" for c in incident_id):
        raise ValueError("Invalid incident ID")
    path = DATA_DIR / f"{incident_id}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Incident not found: {incident_id}")
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("id") != incident_id:
        raise ValueError("Incident fixture ID mismatch")
    return data

def infrastructure_registry() -> ToolRegistry:
    registry = ToolRegistry()
    registry.register(Tool("get_incident", "Read a local incident record by ID.",
        {"type": "object", "properties": {"incident_id": {"type": "string"}},
         "required": ["incident_id"], "additionalProperties": False}, get_incident))
    return registry
