"""A production change request cannot borrow a broad or stale approval."""

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from src.policy.audit import AuditSink
from src.policy.engine import Approval, PolicyContext, arguments_digest
from src.tools.executor import ToolExecutor
from src.tools.registry import Tool, ToolRegistry


class GovernanceScenario(unittest.TestCase):
    def test_wrong_target_is_denied_then_exact_request_is_audited(self):
        with tempfile.TemporaryDirectory() as directory:
            marker = Path(directory) / "changed"
            registry = ToolRegistry()

            def restart(service):
                marker.write_text(service)
                return {"accepted": True, "service": service}

            registry.register(Tool(
                "restart", "Restart target", {
                    "properties": {"service": {"type": "string"}}, "required": ["service"]},
                restart, risk="high", side_effects=True,
                resource_argument="service", verifier=lambda result: marker.read_text() == result["service"]))
            sink = AuditSink(Path(directory) / "audit.jsonl", b"scenario-key" * 4)
            approval = Approval("INC-123:approval", "oncall-7", "restart", "api",
                                arguments_digest({"service": "api"}),
                                datetime.now(timezone.utc) + timedelta(minutes=5))
            executor = ToolExecutor(registry, frozenset({"restart"}),
                                    PolicyContext("prod", actor_id="oncall-7",
                                                  scopes=frozenset(), allow_mutations=True,
                                                  approvals=(approval,)), sink)
            denied = executor.execute("restart", {"service": "database"})
            self.assertEqual(denied.error_code, "policy_denied")
            self.assertFalse(marker.exists())
            approved = executor.execute("restart", {"service": "api"})
            self.assertTrue(approved.ok)
            self.assertEqual(marker.read_text(), "api")
            records = sink.verify()
            self.assertEqual([event["decision"] for event in records],
                             ["deny", "allow", "allow"])
            self.assertEqual(records[-1]["outcome"], "SUCCESS")
