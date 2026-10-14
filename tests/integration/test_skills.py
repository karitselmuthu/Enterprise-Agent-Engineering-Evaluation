import unittest

from src.mcp.server import mcp
from src.skills.executor import SkillExecutionError, SkillRunner
from src.skills.loader import load_skills


class SkillRunnerTests(unittest.IsolatedAsyncioTestCase):
    async def test_incident_skill_returns_structured_output(self):
        result = await SkillRunner(load_skills(), mcp).run(
            "incident_analysis", {"incident_id": "INC-001"})
        self.assertTrue(result.ok)
        self.assertEqual(result.output["tool"], "incident_record")
        self.assertEqual(result.output["data"]["id"], "INC-001")

    async def test_service_skill_returns_text(self):
        result = await SkillRunner(load_skills(), mcp).run(
            "service_health", {"service": "api"})
        self.assertEqual(result.output, "Service api is degraded.")

    async def test_error_behavior_and_input_validation(self):
        runner = SkillRunner(load_skills(), mcp)
        failure = await runner.run("incident_analysis", {"incident_id": "INC-999"})
        self.assertFalse(failure.ok)
        with self.assertRaises(SkillExecutionError):
            await runner.run("service_health", {"service": "missing"})
        with self.assertRaises(ValueError):
            await runner.run("service_health", {"wrong": "api"})

    async def test_host_policy_restricts_skill(self):
        runner = SkillRunner(load_skills(), mcp,
                             host_allowed=frozenset({"incident_record"}))
        with self.assertRaises(PermissionError):
            await runner.run("service_health", {"service": "api"})

    async def test_declared_error_behavior_handles_backend_failure(self):
        class BrokenBackend:
            def select_tool(self, request, tools):
                raise RuntimeError("model unavailable")
        runner = SkillRunner(load_skills(), mcp, backend=BrokenBackend())
        returned = await runner.run("incident_analysis", {"incident_id": "INC-001"})
        self.assertFalse(returned.ok)
        self.assertIn("model unavailable", returned.error)
        with self.assertRaises(SkillExecutionError):
            await runner.run("service_health", {"service": "api"})
