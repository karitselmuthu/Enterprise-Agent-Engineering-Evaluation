import unittest
from time import sleep
from src.agents.runtime import IncidentAgent
from src.tools.executor import ToolExecutor
from src.tools.mock_infrastructure import infrastructure_registry
from src.tools.registry import Tool, ToolRegistry
from src.llm.local_backend import OllamaBackend

class ToolCallingTests(unittest.TestCase):
    def test_agent_uses_incident_tool(self):
        state = IncidentAgent().run("INC-001")
        self.assertTrue(state.tool_results[0].ok)
        self.assertIn("Database connection pool saturation", state.answer)
        self.assertEqual([event["stage"] for event in state.trace],
                         ["selection", "execution", "interpretation"])

    def test_selects_service_tool_and_interprets_result(self):
        state = IncidentAgent().run("Check health of service api")
        self.assertEqual(state.tool_results[0].name, "get_service_status")
        self.assertEqual(state.answer, "Service api is degraded.")

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

    def test_unknown_tool_is_rejected(self):
        result = ToolExecutor(infrastructure_registry(), frozenset({"missing"})).execute(
            "missing", {})
        self.assertEqual(result.error_code, "unknown_tool")

    def test_tool_failure_is_reported(self):
        registry = ToolRegistry()
        def fail() -> None:
            raise RuntimeError("upstream unavailable")
        registry.register(Tool("fail", "Fail", {"properties": {}}, fail))
        result = ToolExecutor(registry, frozenset({"fail"})).execute("fail", {})
        self.assertEqual(result.error_code, "execution_failed")
        self.assertIn("upstream unavailable", result.error)

    def test_timeout_is_reported(self):
        registry = ToolRegistry()
        def slow() -> None:
            sleep(0.1)
        registry.register(Tool("slow", "Slow", {"properties": {}}, slow))
        result = ToolExecutor(registry, frozenset({"slow"})).execute(
            "slow", {}, timeout_seconds=0.01)
        self.assertEqual(result.error_code, "timeout")

    def test_ollama_backend_parses_tool_call_and_interprets_result(self):
        payloads = []
        def post(payload):
            payloads.append(payload)
            if "tools" in payload:
                return {"message": {"role": "assistant", "content": "", "tool_calls": [
                    {"function": {"name": "get_service_status",
                                  "arguments": {"service": "api"}}}]}}
            return {"message": {"role": "assistant", "content": "API is degraded."}}
        agent = IncidentAgent(backend=OllamaBackend("test-model", post=post))
        state = agent.run("Check API health")
        self.assertEqual(state.tool_results[0].name, "get_service_status")
        self.assertEqual(state.answer, "API is degraded.")
        self.assertEqual(payloads[1]["messages"][-1]["role"], "tool")
