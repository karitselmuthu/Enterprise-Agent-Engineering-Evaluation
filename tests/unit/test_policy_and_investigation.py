"""Policy, budget, and state transitions are enforced outside the planner."""

import unittest
import tempfile
from pathlib import Path

from src.agents.investigation import InvestigationBudget, InvestigationRecord
from src.policy.engine import PolicyContext
from src.tools.executor import ToolExecutor, ToolStatus
from src.tools.registry import Tool, ToolRegistry


class PolicyAndInvestigationTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.registry = ToolRegistry()

        def restart(service: str):
            self.calls.append(service)
            return {"service": service, "accepted": True}

        self.registry.register(Tool(
            "restart", "Restart a service", {"type": "object",
            "properties": {"service": {"type": "string"}}, "required": ["service"]},
            restart, risk="high", side_effects=True, idempotent=False,
            required_scopes=frozenset({"service:restart"}),
            verifier=lambda result: result["service"] in self.calls))

    def test_mutation_denied_by_default_even_when_name_allowed(self):
        result = ToolExecutor(self.registry, frozenset({"restart"})).execute(
            "restart", {"service": "api"})
        self.assertEqual(result.error_code, "policy_denied")
        self.assertEqual(result.status, ToolStatus.POLICY_DENIED)
        self.assertEqual(self.calls, [])

    def test_scope_and_approval_are_separate_requirements(self):
        arguments = {"service": "api"}
        without_scope = ToolExecutor(self.registry, frozenset({"restart"}),
            PolicyContext(environment="prod", allow_mutations=True,
                          approved_tools=frozenset({"restart"}))).execute("restart", arguments)
        self.assertEqual(without_scope.error_code, "policy_denied")
        without_approval = ToolExecutor(self.registry, frozenset({"restart"}),
            PolicyContext(environment="prod", allow_mutations=True,
                          scopes=frozenset({"service:restart"}))).execute("restart", arguments)
        self.assertEqual(without_approval.error_code, "policy_denied")
        self.assertEqual(self.calls, [])
        approved = ToolExecutor(self.registry, frozenset({"restart"}),
            PolicyContext(environment="prod", allow_mutations=True,
                          scopes=frozenset({"service:restart"}),
                          approved_tools=frozenset({"restart"}))).execute("restart", arguments)
        self.assertTrue(approved.ok)
        self.assertTrue(approved.side_effect_verified)
        self.assertEqual(self.calls, ["api"])

    def test_mutation_without_verifier_is_rejected(self):
        registry = ToolRegistry()
        registry.register(Tool("unsafe", "Unsafe", {"properties": {}},
                               lambda: self.calls.append("unsafe"), side_effects=True))
        result = ToolExecutor(registry, frozenset({"unsafe"}),
            PolicyContext(allow_mutations=True)).execute("unsafe", {})
        self.assertEqual(result.error_code, "policy_denied")
        self.assertEqual(self.calls, [])

    def test_post_action_verification_failure_is_explicit(self):
        registry = ToolRegistry()
        registry.register(Tool("change", "Change", {"properties": {}},
                               lambda: {"accepted": True}, side_effects=True,
                               verifier=lambda _result: False))
        result = ToolExecutor(registry, frozenset({"change"}),
            PolicyContext(allow_mutations=True)).execute("change", {})
        self.assertEqual(result.error_code, "verification_failed")
        self.assertFalse(result.ok)

    def test_illegal_transition_and_budget(self):
        record = InvestigationRecord("T-1", InvestigationBudget(max_tool_calls=1))
        with self.assertRaisesRegex(ValueError, "Illegal transition"):
            record.transition("completed")
        record.transition("observe")
        self.assertTrue(record.reserve_tool_call())
        self.assertFalse(record.reserve_tool_call())
        self.assertEqual(record.events[-1]["kind"], "budget_exceeded")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "events.jsonl"
            record.write_jsonl(path)
            self.assertEqual(len(path.read_text().splitlines()), len(record.events))
            with self.assertRaises(FileExistsError):
                record.write_jsonl(path)
