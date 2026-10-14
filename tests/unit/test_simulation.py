"""Deterministic and negative checks for public replay data."""

import json
import tempfile
import unittest
from pathlib import Path

from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.event_generator import build_records
from simulation.scenario_loader import load_scenarios


class SimulationUnitTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = load_scenarios()

    def test_twenty_distinct_scenarios_and_timeline(self):
        self.assertEqual(len(self.scenarios), 20)
        self.assertEqual([event["minute"] for event in self.scenarios["SIM-004"].events],
                         list(range(0, 40, 5)))
        self.assertTrue(all([event["minute"] for event in item.events] == [0, 5, 10, 15]
                            for identifier, item in self.scenarios.items()
                            if identifier != "SIM-004"))

    def test_committed_fixtures_match_deterministic_generator(self):
        public, labels = build_records()
        for path, records in (("data/simulation/scenarios.jsonl", public),
                              ("data/evaluation_datasets/simulation_ground_truth.jsonl", labels)):
            observed = [json.loads(line) for line in Path(path).read_text().splitlines()]
            self.assertEqual(observed, records)

    def test_clock_rejects_invalid_time(self):
        clock = VirtualClock()
        with self.assertRaises(ValueError):
            clock.seek(-1)
        with self.assertRaises(ValueError):
            clock.advance(True)
        clock.advance(5)
        self.assertEqual(clock.minute, 5)

    def test_future_observations_are_invisible_until_clock_advances(self):
        engine = ReplayEngine(self.scenarios["SIM-004"])
        with self.assertRaisesRegex(KeyError, "not yet raised"):
            engine.incident("SIM-004")
        self.assertEqual(len(engine.metrics("prod-app-004")["samples"]), 1)
        self.assertFalse(any("exhausted" in entry["message"]
                             for entry in engine.logs("payment-service")["entries"]))
        engine.clock.seek(20)
        self.assertEqual(len(engine.metrics("prod-app-004")["samples"]), 5)
        self.assertTrue(any("exhausted" in entry["message"]
                            for entry in engine.logs("payment-service")["entries"]))

    def test_inconsistent_absolute_timestamp_is_rejected(self):
        public, _ = build_records()
        public[0]["events"][1]["timestamp"] = "2026-10-14T11:05:00Z"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad_time.jsonl"
            path.write_text(json.dumps(public[0]) + "\n")
            with self.assertRaisesRegex(ValueError, "timestamps must match"):
                load_scenarios(path)

    def test_public_dataset_rejects_hidden_labels(self):
        public = {"scenario_id": "x", "incident": {"id": "x", "server_id": "s",
                  "service": "v", "summary": "alert"}, "events": [{"minute": 0,
                  "metrics": {}, "logs": [], "status": "open", "root_cause": "secret"}]}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text(json.dumps(public) + "\n")
            with self.assertRaisesRegex(ValueError, "private labels"):
                load_scenarios(path)

    def test_missing_metrics_and_timeout(self):
        missing = ReplayEngine(self.scenarios["SIM-011"], VirtualClock(10))
        self.assertEqual(missing.metrics("prod-app-011")["status"], "missing")
        timed = ReplayEngine(self.scenarios["SIM-012"], VirtualClock(10))
        with self.assertRaises(TimeoutError):
            timed.metrics("prod-app-012")
        timed.clock.seek(15)
        self.assertEqual(timed.metrics("prod-app-012")["status"], "available")

    def test_recovery_repeated_alerts_and_conflicting_signals(self):
        recovery = ReplayEngine(self.scenarios["SIM-014"], VirtualClock(10))
        high_cpu = recovery.metrics("prod-app-014")["samples"][-1]["cpu_percent"]
        recovery.clock.advance(5)
        self.assertEqual(recovery.incident("SIM-014")["status"], "resolved")
        self.assertLess(recovery.metrics("prod-app-014")["samples"][-1]["cpu_percent"], high_cpu)

        repeated = ReplayEngine(self.scenarios["SIM-015"], VirtualClock(10))
        messages = [entry["message"] for entry in repeated.logs("edge-router")["entries"]]
        self.assertGreater(messages.count("Latency alert repeated"), 1)

        conflict = ReplayEngine(self.scenarios["SIM-013"], VirtualClock(10))
        self.assertLess(conflict.metrics("prod-app-013")["samples"][-1]["cpu_percent"], 50)
        self.assertTrue(any("CPU saturation" in entry["message"]
                            for entry in conflict.logs("search-api")["entries"]))

    def test_unknown_resource_is_rejected(self):
        engine = ReplayEngine(self.scenarios["SIM-001"])
        with self.assertRaises(KeyError):
            engine.incident("SIM-999")
        with self.assertRaises(KeyError):
            engine.logs("unrelated-service")
