"""Safe starter plan."""
def plan(incident_id: str) -> list[tuple[str, dict[str, str]]]:
    if not incident_id.strip():
        raise ValueError("incident_id is required")
    return [("get_incident", {"incident_id": incident_id})]
