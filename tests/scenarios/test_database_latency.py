"""Full database-latency investigation and deterministic fault injection."""

import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.faults import database_latency_variants
from simulation.scenario_loader import load_scenarios
from simulation.scenario_loader import Scenario
from src.agents.simulation_agent import SimulationInvestigator
from src.evaluation.database_latency_eval import evaluate_database_latency
from src.evaluation.process_validation import inspect_process


class DatabaseLatencyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenario = load_scenarios()["SIM-004"]

    def run_variant(self, name: str, minute: int = 25):
        scenario = database_latency_variants(self.scenario, minute)[name]
        engine = ReplayEngine(scenario, VirtualClock(minute))
        return SimulationInvestigator(replay_tools(engine)).run("SIM-004")

    def test_time_bounded_authorized_database_observation(self):
        engine = ReplayEngine(self.scenario, VirtualClock(15))
        result = replay_tools(engine).execute("get_database_metrics",
                                              {"database_id": "payment-db"})
        self.assertTrue(result.ok)
        self.assertEqual([item["minute"] for item in result.content["samples"]],
                         [0, 5, 10, 15])
        denied = replay_tools(engine, allowed=frozenset({
            "get_incident_record", "get_server_metrics", "get_application_logs"})).execute(
                "get_database_metrics", {"database_id": "payment-db"})
        self.assertEqual(denied.error_code, "permission_denied")

    def test_baseline_hypothesis_has_metric_evidence_and_ordered_events(self):
        state = self.run_variant("baseline")
        self.assertEqual(state.finding.status, "supported_hypothesis")
        self.assertEqual(state.finding.hypothesis, "database connection pool exhaustion")
        self.assertEqual(len(state.finding.evidence_ids), 2)
        self.assertTrue(all(f"[{identifier}]" in state.answer
                            for identifier in state.finding.evidence_ids))
        self.assertTrue(inspect_process(state)["citation_integrity"])
        self.assertLess(next(i for i, event in enumerate(state.investigation.events)
                             if event["kind"] == "latency_detected"),
                        next(i for i, event in enumerate(state.investigation.events)
                             if event["kind"] == "tool_proposed" and
                             event["tool"] == "get_database_metrics"))

    def test_missing_and_timeout_do_not_assert_cause_from_log(self):
        for variant in ("missing_metrics", "tool_timeout"):
            with self.subTest(variant=variant):
                state = self.run_variant(variant)
                self.assertEqual(state.finding.status, "insufficient_evidence")
                self.assertIsNone(state.finding.hypothesis)
                self.assertIn("Insufficient evidence", state.answer)
                self.assertFalse(any(card.signal == "database_connection_pool"
                                     for card in state.evidence_cards))
        timed = self.run_variant("tool_timeout")
        self.assertEqual(next(result.error_code for result in timed.tool_results
                              if result.name == "get_database_metrics"), "timeout")

    def test_misleading_log_is_flagged_against_metrics(self):
        state = self.run_variant("misleading_logs")
        self.assertEqual(state.finding.status, "supported_hypothesis")
        self.assertIn("conflicts", state.answer)
        self.assertTrue(any(event.get("conflicting_log") for event in
                            state.investigation.events if event["kind"] == "hypothesis_verified"))

    def test_early_pool_pressure_is_not_reported_as_exhaustion(self):
        state = self.run_variant("baseline", minute=10)
        self.assertEqual(state.finding.status, "insufficient_evidence")
        self.assertIsNone(state.finding.hypothesis)

    def test_stale_pool_sample_does_not_support_current_cause(self):
        events = deepcopy(list(self.scenario.events))
        next(event for event in events if event["minute"] == 25)["database_metrics"] = None
        scenario = Scenario(self.scenario.scenario_id, self.scenario.incident,
                            tuple(events), self.scenario.allowed_tools)
        state = SimulationInvestigator(replay_tools(
            ReplayEngine(scenario, VirtualClock(25)))).run("SIM-004")
        self.assertEqual(state.finding.status, "insufficient_evidence")
        self.assertIn("stale", state.answer)

    def test_malformed_database_sample_is_rejected_at_load(self):
        public = json.loads(next(line for line in Path(
            "data/simulation/scenarios.jsonl").read_text().splitlines()
            if '"scenario_id": "SIM-004"' in line))
        public["events"][4]["database_metrics"]["active_connections"] = "forty"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.jsonl"
            path.write_text(json.dumps(public) + "\n")
            with self.assertRaisesRegex(ValueError, "database_metrics"):
                load_scenarios(path)

    def test_evaluator_detects_broken_metric_evidence(self):
        report = evaluate_database_latency()
        self.assertTrue(report["passed"])
        self.assertEqual(report["variant_count"], 4)
        self.assertEqual(report["mean_workflow_score"], 1)
        public = json.loads(next(line for line in Path(
            "data/simulation/scenarios.jsonl").read_text().splitlines()
            if '"scenario_id": "SIM-004"' in line))
        for event in public["events"]:
            event["database_metrics"]["active_connections"] = 10
            event["database_metrics"]["waiting_requests"] = 0
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenario.jsonl"
            path.write_text(json.dumps(public) + "\n")
            broken = evaluate_database_latency(public_path=path)
        self.assertFalse(broken["passed"])
        self.assertLess(broken["mean_workflow_score"], 1)
        self.assertFalse(next(item for item in broken["results"]
                              if item["variant"] == "baseline")["checks"]["hypothesis_outcome"])
