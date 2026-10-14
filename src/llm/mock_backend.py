"""Deterministic response builder."""
class MockBackend:
    def generate(self, incident: dict) -> str:
        return (f"Incident {incident['id']}: {incident['title']}. "
                f"Impact: {incident['impact']}. "
                f"Suspected cause: {incident['suspected_cause']}. "
                f"Recommended action: {incident['recommended_action']}.")
