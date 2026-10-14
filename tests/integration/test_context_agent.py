import tempfile
import unittest
from pathlib import Path

from src.context.agent import ContextAwareIncidentAgent
from src.context.manager import ContextManager
from src.context.token_budget import ContextBudget
from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp


class ContextAgentTests(unittest.IsolatedAsyncioTestCase):
    async def test_long_session_stays_within_budget_and_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            manager = ContextManager(ContextBudget(320, 80, 20))
            agent = ContextAwareIncidentAgent(path, MCPIncidentAgent(mcp), manager)
            await agent.investigate("case", "Investigate INC-001")
            agent.long_term.add_memory("case", "fact", "Pool reached 95%", approved=True)
            for number in range(15):
                agent.long_term.save_investigation(
                    "case", "Investigate INC-001", "Prior finding " + "detail " * 20,
                    user_message=f"Follow-up {number} " + "context " * 20)
            restarted = ContextAwareIncidentAgent(path, MCPIncidentAgent(mcp), manager)
            state = await restarted.investigate("case", "Continue investigation")
            context_event = state.trace[0]
            self.assertEqual(context_event["stage"], "context")
            self.assertLessEqual(context_event["estimated_tokens"],
                                 context_event["input_budget"])
            self.assertIn("Pool reached 95%", state.request)
            self.assertIn("database_connections.md", state.answer)
            self.assertEqual(restarted.resume("case").current_task, "Investigate INC-001")
