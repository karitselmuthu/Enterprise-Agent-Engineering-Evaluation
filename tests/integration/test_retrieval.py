import tempfile
import unittest
from pathlib import Path

from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp
from src.retrieval.agent import RetrievalIncidentAgent
from src.retrieval.retriever import RunbookRetriever


class RetrievalTests(unittest.IsolatedAsyncioTestCase):
    def test_relevant_runbooks_rank_first(self):
        retriever = RunbookRetriever()
        cases = {
            "database connection pool saturation": "database_connections.md",
            "Kubernetes pod restart": "kubernetes.md",
            "high CPU utilization": "high_cpu.md",
            "network latency DNS": "network_latency.md",
            "application deployment failed rollout": "deployment_failures.md",
        }
        for query, expected_file in cases.items():
            with self.subTest(query=query):
                self.assertEqual(Path(retriever.search(query, 1)[0].section.path).name,
                                 expected_file)

    def test_empty_or_unmatched_query_has_no_hits(self):
        self.assertEqual(RunbookRetriever().search("xyznonexistentterm"), [])

    async def test_agent_cites_and_persists_retrieved_guidance(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.sqlite3"
            agent = RetrievalIncidentAgent(path, MCPIncidentAgent(mcp))
            state = await agent.investigate("case", "Investigate INC-001")
            self.assertIn("database_connections.md", state.answer)
            self.assertIn("Connection pool exhaustion", state.answer)
            self.assertTrue(any(event["stage"] == "retrieval" for event in state.trace))
            restarted = RetrievalIncidentAgent(path, MCPIncidentAgent(mcp))
            self.assertIn("database_connections.md",
                          restarted.long_term.get_investigation("case")["answer"])
