"""Exercise evaluation against real MCP and retrieval agent runs."""

import tempfile
import unittest
from pathlib import Path

from src.evaluation.agent_evaluator import AgentCase, ExpectedCall, evaluate_agent_state
from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp
from src.retrieval.agent import RetrievalIncidentAgent


class EvaluationPipelineTests(unittest.IsolatedAsyncioTestCase):
    async def test_mcp_investigation_is_scored(self):
        case = AgentCase("mcp-incident", "Investigate INC-001",
                         (ExpectedCall("incident_record", {"incident_id": "INC-001"}),),
                         ("database connection pool", "slow queries"))
        state = await MCPIncidentAgent(mcp).run(case.request)
        score = evaluate_agent_state(case, state)
        self.assertTrue(score["trajectory_exact"])
        self.assertTrue(score["execution_success"])
        self.assertEqual(score["answer_term_recall"], 1)

    async def test_mcp_failure_is_not_counted_as_success(self):
        case = AgentCase("missing", "Investigate INC-999",
                         (ExpectedCall("incident_record", {"incident_id": "INC-999"}),),
                         ("incident record",))
        state = await MCPIncidentAgent(mcp).run(case.request)
        score = evaluate_agent_state(case, state)
        self.assertTrue(score["trajectory_exact"])
        self.assertFalse(score["execution_success"])
        self.assertEqual(score["tool_failures"], ["mcp_tool_error"])

    async def test_retrieval_guidance_is_scored_after_mcp_call(self):
        with tempfile.TemporaryDirectory() as directory:
            agent = RetrievalIncidentAgent(Path(directory) / "memory.sqlite3",
                                           MCPIncidentAgent(mcp))
            case = AgentCase("retrieval", "Investigate INC-001",
                             (ExpectedCall("incident_record", {"incident_id": "INC-001"}),),
                             ("database connection pool", "slow queries"))
            state = await agent.investigate("session", case.request)
            score = evaluate_agent_state(case, state)
            self.assertTrue(score["execution_success"])
            self.assertEqual(score["answer_term_recall"], 1)
            self.assertIn("database_connections.md", state.answer)
            self.assertTrue(any(item.get("stage") == "retrieval" for item in state.trace))
