"""Check that scenario labels are backed by time-bounded public evidence."""

import json
import tempfile
import unittest
from pathlib import Path

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import load_scenarios
from src.agents.simulation_agent import SimulationInvestigator
from src.evaluation.simulation_eval import load_ground_truth


class ScenarioCatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = load_scenarios()
        cls.labels = load_ground_truth()

    def engine(self, identifier: str, minute: int = 10) -> ReplayEngine:
        return ReplayEngine(self.scenarios[identifier], VirtualClock(minute))

    def test_complete_private_rubrics_for_all_25(self):
        self.assertEqual(set(self.scenarios), set(self.labels))
        self.assertEqual(len(self.scenarios), 25)
        self.assertEqual(len({label["scenario_name"] for label in self.labels.values()}), 25)
        for identifier, label in self.labels.items():
            with self.subTest(identifier=identifier):
                self.assertEqual(label["affected_service"],
                                 self.scenarios[identifier].incident["service"])
                self.assertGreaterEqual(len(label["expected_findings"]), 2)
                self.assertGreater(len(label["expected_behavior"]), 30)
                self.assertGreaterEqual(len(self.scenarios[identifier].events), 4)
        public = Path("data/simulation/scenarios.jsonl").read_text()
        self.assertNotIn('"expected_findings"', public)
        self.assertNotIn('"expected_behavior"', public)
        self.assertNotIn('"root_cause"', public)
        self.assertIsNone(self.labels["SIM-017"]["root_cause"])
        self.assertIsNone(self.labels["SIM-011"]["root_cause"])

    def test_core_incident_signals(self):
        cpu = self.engine("SIM-001", 15).metrics("prod-app-001")["samples"]
        self.assertTrue(all(sample["cpu_percent"] >= 90 for sample in cpu[-2:]))
        memory = self.engine("SIM-002").metrics("prod-app-002")["samples"]
        self.assertEqual([sample["memory_percent"] for sample in memory], [48, 72, 91])
        disk = self.engine("SIM-003").metrics("prod-app-003")["samples"][-1]
        self.assertGreaterEqual(disk["disk_percent"], 95)
        payment = self.engine("SIM-004", 25)
        self.assertIn("pool exhaustion", payment.logs("payment-service")["entries"][-1]["message"])
        self.assertIn("Connection refused", self.engine("SIM-005").logs("billing-api")["entries"][-1]["message"])

    def test_pod_and_network_evidence_are_separate_permitted_tools(self):
        pod = self.engine("SIM-006")
        pod_result = replay_tools(pod).execute("get_pod_events", {"pod": "inventory-worker-0"})
        self.assertTrue(pod_result.ok)
        self.assertEqual(pod_result.content["entries"][-1]["reason"], "BackOff")
        self.assertTrue(any("exited" in entry["message"] for entry in
                            pod.logs("inventory-worker")["entries"]))
        network = replay_tools(self.engine("SIM-007")).execute(
            "get_service_network_metrics", {"service": "checkout-edge"})
        self.assertTrue(network.ok)
        latest = {item["service"]: item["latency_ms"]
                  for item in network.content["samples"] if item["minute"] == 10}
        self.assertGreater(latest["inventory-api"], 200)
        self.assertLess(latest["catalog-api"], 30)
        denied = replay_tools(self.engine("SIM-001")).execute(
            "get_pod_events", {"pod": "inventory-worker-0"})
        self.assertEqual(denied.error_code, "permission_denied")
        early = self.engine("SIM-006", 0).pod_events("inventory-worker-0")
        self.assertEqual(early["entries"], [])

    def test_deployment_auth_and_multiple_incidents(self):
        release = self.engine("SIM-008").logs("fulfillment-api")["entries"]
        self.assertIn("release deployed", release[1]["message"])
        self.assertIn("Errors increased", release[2]["message"])
        auth = self.engine("SIM-009").logs("identity-service")["entries"]
        self.assertIn("Authentication rejected", auth[-1]["message"])
        multi = self.engine("SIM-010")
        self.assertEqual(multi.incident("SIM-010-B")["service"], "billing-api")
        self.assertIn("CPU queue", multi.logs("payment-gateway")["entries"][-1]["message"])
        self.assertIn("database connection", multi.logs("billing-api")["entries"][-1]["message"])
        state = SimulationInvestigator(replay_tools(multi)).run("SIM-010")
        self.assertIn("separate incident SIM-010-B", state.answer)
        self.assertTrue(any(event.get("arguments") == {"incident_id": "SIM-010-B"}
                            for event in state.trace))

    def test_evidence_gaps_conflict_recovery_and_policy(self):
        self.assertEqual(self.engine("SIM-011").metrics("prod-app-011")["samples"], [])
        self.assertEqual(self.engine("SIM-011").logs("analytics-api")["entries"], [])
        with self.assertRaises(TimeoutError):
            self.engine("SIM-012").metrics("prod-app-012")
        conflict = self.engine("SIM-013")
        self.assertLess(conflict.metrics("prod-app-013")["samples"][-1]["cpu_percent"], 50)
        self.assertIn("CPU saturation", conflict.logs("search-api")["entries"][-1]["message"])
        recovery = self.engine("SIM-014", 15)
        self.assertEqual(recovery.incident("SIM-014")["status"], "resolved")
        self.assertLess(recovery.metrics("prod-app-014")["samples"][-1]["cpu_percent"], 50)
        denied = replay_tools(self.engine("SIM-016")).execute(
            "get_server_metrics", {"server_id": "prod-app-016"})
        self.assertEqual(denied.error_code, "permission_denied")
        self.assertEqual(self.engine("SIM-017").incident("SIM-017")["status"], "healthy")

    def test_additional_distinct_failure_modes(self):
        self.assertIn("NXDOMAIN", self.engine("SIM-021").logs("shipping-api")["entries"][-1]["message"])
        replica = self.engine("SIM-022").metrics("prod-app-022")["samples"]
        self.assertGreater(replica[-1]["replication_lag_seconds"], replica[0]["replication_lag_seconds"])
        io = self.engine("SIM-023").metrics("prod-app-023")["samples"][-1]
        self.assertGreater(io["disk_io_latency_ms"], 100)
        self.assertLess(io["disk_percent"], 50)
        self.assertIn("HTTP 429", self.engine("SIM-024").logs("public-api")["entries"][-1]["message"])
        regional = self.engine("SIM-025").network_peers("regional-gateway")["samples"]
        latest = {item["service"]: item["latency_ms"]
                  for item in regional if item["minute"] == 10}
        self.assertEqual(len([value for value in latest.values() if value > 200]), 2)
        self.assertLess(latest["local-api"], 30)

    def test_rejects_malformed_specialized_observations(self):
        raw = json.loads(Path("data/simulation/scenarios.jsonl").read_text().splitlines()[5])
        raw["events"][2]["pod_events"][0]["timestamp"] = "2026-10-14T10:00:00Z"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text(json.dumps(raw) + "\n")
            with self.assertRaisesRegex(ValueError, "pod_events"):
                load_scenarios(path)

    def test_agent_uses_timeline_for_trends_and_uncertainty(self):
        expectations = {
            "SIM-001": (15, "CPU remained above 90%"),
            "SIM-002": (10, "memory rose from 48% to 91%"),
            "SIM-003": (10, "disk is 97% used"),
            "SIM-008": (10, "errors followed release"),
            "SIM-013": (10, "measurements conflict"),
        }
        for identifier, (minute, expected) in expectations.items():
            with self.subTest(identifier=identifier):
                state = SimulationInvestigator(replay_tools(self.engine(identifier, minute))).run(
                    identifier)
                self.assertIn(expected.casefold(), state.answer.casefold())
