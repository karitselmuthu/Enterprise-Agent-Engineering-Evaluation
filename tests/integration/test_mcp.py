import unittest

from mcp import Client
from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp


class MCPTests(unittest.IsolatedAsyncioTestCase):
    async def test_discovery_and_structured_invocation(self):
        state = await MCPIncidentAgent(mcp).run("Investigate INC-001")
        self.assertEqual(state.trace[0]["tools"], ["incident_record", "service_status"])
        self.assertTrue(state.tool_results[0].ok)
        self.assertEqual(state.tool_results[0].content["id"], "INC-001")

    async def test_server_error_becomes_tool_failure(self):
        state = await MCPIncidentAgent(mcp).run("Investigate INC-999")
        self.assertFalse(state.tool_results[0].ok)
        self.assertEqual(state.tool_results[0].error_code, "mcp_tool_error")

    async def test_server_validates_input_schema(self):
        async with Client(mcp) as client:
            result = await client.call_tool("incident_record", {"incident_id": 12})
            self.assertTrue(result.is_error)

    async def test_client_rejects_disallowed_tool(self):
        class Selector:
            def select_tool(self, request, tools):
                return "service_status", {"service": "api"}
            def interpret(self, request, result):
                return result.error or "ok"
        state = await MCPIncidentAgent(
            mcp, allowed=frozenset({"incident_record"}), backend=Selector()
        ).run("Check API")
        self.assertEqual(state.tool_results[0].error_code, "permission_denied")

    async def test_client_rejects_unknown_tool(self):
        class Selector:
            def select_tool(self, request, tools):
                return "delete_cluster", {}
            def interpret(self, request, result):
                return result.error or "ok"
        state = await MCPIncidentAgent(mcp, backend=Selector()).run("Delete cluster")
        self.assertEqual(state.tool_results[0].error_code, "unknown_tool")
