import tempfile
import time
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.policy.audit import AuditIntegrityError, AuditSink
from src.policy.engine import Approval, PolicyContext, arguments_digest
from src.tools.executor import ToolExecutor
from src.tools.registry import Tool, ToolRegistry


class GovernanceTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.path = Path(temporary.name)
        self.sink = AuditSink(self.path / "audit.jsonl", b"audit-key" * 4)
        self.marker = self.path / "marker"
        registry = ToolRegistry()

        def mutate(service: str):
            self.marker.write_text(service)
            return {"service": service}

        registry.register(Tool("mutate", "Mutate", {
            "properties": {"service": {"type": "string"}}, "required": ["service"]},
            mutate, risk="high", side_effects=True, resource_argument="service",
            verifier=lambda result: result["service"] == self.marker.read_text()))
        self.registry = registry

    def approval(self, *, actor="alice", operation="mutate", resource="api",
                 args=None, expires=None):
        return Approval("APR-42", actor, operation, resource,
                        arguments_digest(args or {"service": "api"}),
                        expires or datetime.now(timezone.utc) + timedelta(minutes=5))

    def execute(self, approval, args=None, actor="alice", sink=True):
        policy = PolicyContext("prod", actor_id=actor, allow_mutations=True,
                               approvals=(approval,))
        return ToolExecutor(self.registry, frozenset({"mutate"}), policy,
                            self.sink if sink else None).execute("mutate", args or {"service": "api"})

    def test_approval_must_match_actor_operation_resource_arguments_and_expiry(self):
        cases = [
            (self.approval(actor="bob"), {"service": "api"}, "alice"),
            (self.approval(operation="delete"), {"service": "api"}, "alice"),
            (self.approval(resource="database"), {"service": "api"}, "alice"),
            (self.approval(args={"service": "database"}), {"service": "api"}, "alice"),
            (self.approval(expires=datetime.now(timezone.utc) - timedelta(seconds=1)),
             {"service": "api"}, "alice"),
        ]
        for approval, args, actor in cases:
            self.assertEqual(self.execute(approval, args, actor).error_code, "policy_denied")
        self.assertFalse(self.marker.exists())
        self.assertTrue(self.execute(self.approval()).ok)

    def test_mutation_requires_durable_audit(self):
        self.assertEqual(self.execute(self.approval(), sink=False).error_code, "policy_denied")
        self.assertFalse(self.marker.exists())

    def test_legacy_name_allowance_does_not_grant_approval(self):
        policy = PolicyContext("prod", actor_id="alice", allow_mutations=True,
                               approved_tools=frozenset({"mutate"}))
        result = ToolExecutor(self.registry, frozenset({"mutate"}), policy,
                              self.sink).execute("mutate", {"service": "api"})
        self.assertEqual(result.error_code, "policy_denied")
        self.assertFalse(self.marker.exists())

    def test_corrupted_audit_blocks_mutation(self):
        self.sink.append(actor_id="alice", operation="mutate", environment="prod",
                         decision="deny", reason="fixture", approval_reference=None)
        self.sink.path.write_text(self.sink.path.read_text().replace("fixture", "altered"))
        self.assertEqual(self.execute(self.approval()).error_code, "policy_denied")
        self.assertFalse(self.marker.exists())

    def test_audit_chain_detects_tampering_and_omits_payload(self):
        self.assertTrue(self.execute(self.approval()).ok)
        events = self.sink.verify()
        self.assertEqual([e["outcome"] for e in events], [None, "SUCCESS"])
        self.assertNotIn("service", self.sink.path.read_text())
        self.assertEqual(events[0]["approval_reference"], "APR-42")
        self.sink.path.write_text(self.sink.path.read_text().replace("SUCCESS", "TIMEOUT"))
        with self.assertRaises(AuditIntegrityError):
            self.sink.verify()

    def test_timeout_terminates_mutating_child_before_delayed_write(self):
        registry = ToolRegistry()

        def slow(service):
            time.sleep(0.2)
            self.marker.write_text(service)
            return {"service": service}

        registry.register(Tool("slow", "Slow", {
            "properties": {"service": {"type": "string"}}, "required": ["service"]},
            slow, risk="high", side_effects=True, resource_argument="service",
            verifier=lambda result: True))
        approval = self.approval(operation="slow")
        result = ToolExecutor(registry, frozenset({"slow"}),
                              PolicyContext("prod", actor_id="alice", allow_mutations=True,
                                            approvals=(approval,)), self.sink).execute(
                                                "slow", {"service": "api"}, timeout_seconds=0.02)
        self.assertEqual(result.error_code, "timeout")
        time.sleep(0.25)
        self.assertFalse(self.marker.exists())


if __name__ == "__main__":
    unittest.main()
