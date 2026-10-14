import tempfile
import unittest
from pathlib import Path

from src.memory.agent import StatefulIncidentAgent
from src.memory.agent import StatefulMCPIncidentAgent
from src.memory.short_term import ShortTermMemory
from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp


class MemoryTests(unittest.TestCase):
    def test_resume_across_agent_instances(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            first = StatefulIncidentAgent(path)
            initial = first.investigate("case-1", "Investigate INC-001")
            self.assertTrue(initial.tool_results[0].ok)
            first.long_term.add_memory("case-1", "note", "Unverified network hypothesis")
            first.long_term.add_memory("case-1", "fact", "Pool was at 95% utilization",
                                       approved=True)

            restarted = StatefulIncidentAgent(path)
            context = restarted.resume("case-1")
            self.assertEqual(context.current_task, "Investigate INC-001")
            self.assertEqual(len(context.conversation), 2)
            self.assertEqual(context.recent_tool_results[0]["name"], "get_incident")
            followup = restarted.investigate("case-1", "Continue investigation")
            self.assertIn("INC-001", followup.answer)
            self.assertIn("Pool was at 95% utilization", followup.answer)
            self.assertNotIn("Unverified network hypothesis", followup.answer)

    def test_session_isolation_and_missing_session(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = StatefulIncidentAgent(Path(directory) / "memory.sqlite3")
            with self.assertRaises(KeyError):
                agent.resume("missing")
            agent.investigate("one", "Investigate INC-001")
            self.assertIsNone(agent.long_term.get_investigation("two"))

    def test_short_term_bounds_recent_results(self):
        memory = ShortTermMemory("case", max_items=2)
        for number in range(3):
            memory.add_message("user", str(number))
            memory.add_tool_result("tool", True, number)
        self.assertEqual(len(memory.conversation), 2)
        self.assertEqual([item["content"] for item in memory.recent_tool_results], [1, 2])


class MCPMemoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_investigation_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            first = StatefulMCPIncidentAgent(path, MCPIncidentAgent(mcp))
            initial = await first.investigate("case", "Investigate INC-001")
            self.assertEqual(initial.tool_results[0].name, "incident_record")
            second = StatefulMCPIncidentAgent(path, MCPIncidentAgent(mcp))
            self.assertEqual(second.resume("case").recent_tool_results[0]["name"],
                             "incident_record")
            followup = await second.investigate("case", "Continue investigation")
            self.assertIn("INC-001", followup.answer)
