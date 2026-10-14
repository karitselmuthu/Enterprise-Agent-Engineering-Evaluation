import unittest
from src.agents.runtime import IncidentAgent
from src.tools.executor import ToolExecutor
from src.tools.mock_infrastructure import infrastructure_registry

class ToolCallingTests(unittest.TestCase):
    def test_agent_uses_incident_tool(self):
        state = IncidentAgent().run("INC-001")
        self.assertTrue(state.tool_results[0].ok)
        self.assertIn("Database connection pool saturation", state.answer)

    def test_denied_tool_never_executes(self):
        result = ToolExecutor(infrastructure_registry(), frozenset()).execute(
            "get_incident", {"incident_id": "INC-001"})
        self.assertFalse(result.ok)
        self.assertIn("not permitted", result.error)

    def test_schema_rejects_extra_argument(self):
        result = ToolExecutor(infrastructure_registry(), frozenset({"get_incident"})).execute(
            "get_incident", {"incident_id": "INC-001", "surprise": 1})
        self.assertFalse(result.ok)
        self.assertIn("unknown", result.error)
