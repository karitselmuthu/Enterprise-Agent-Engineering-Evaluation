"""Scenario-level scoring uses observations and allows multiple tool orders."""

import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation.scenario_validation import evaluate_scenarios, required_tools_selected


class ScenarioValidationTests(unittest.TestCase):
    def test_baseline_report_is_honest_about_quality_gaps(self):
        report = evaluate_scenarios()
        self.assertEqual(report["scenario_count"], 25)
        self.assertTrue(report["foundation_passed"])
        self.assertEqual(report["tool_selection_rate"], 1)
        self.assertEqual(report["evidence_retrieval_rate"], 1)
        self.assertEqual(report["root_cause_supported_proxy_rate"], 0)
        self.assertGreater(report["recommendation_cue_rate"], 0)
        self.assertLess(report["recommendation_cue_rate"], 1)
        self.assertIsNone(next(item for item in report["results"]
                               if item["scenario_id"] == "SIM-017")["root_cause_supported_proxy"])

    def test_valid_tool_orders_and_extra_calls(self):
        expected = ["get_incident_record", "get_server_metrics", "get_application_logs"]
        self.assertTrue(required_tools_selected(expected, list(reversed(expected))))
        self.assertTrue(required_tools_selected(expected, ["get_application_logs", *expected]))
        self.assertFalse(required_tools_selected(expected, expected[:2]))

    def test_missing_source_evidence_fails_that_scenario(self):
        public = [json.loads(line) for line in Path("data/simulation/scenarios.jsonl").read_text(
            encoding="utf-8").splitlines()]
        for event in public[0]["events"]:
            for log in event["logs"]:
                log["message"] = "Unrelated observation"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "scenarios.jsonl"
            path.write_text("".join(json.dumps(item) + "\n" for item in public), encoding="utf-8")
            report = evaluate_scenarios(public_path=path)
        case = next(item for item in report["results"] if item["scenario_id"] == "SIM-001")
        self.assertTrue(case["tool_selection"])
        self.assertFalse(case["evidence_retrieved"])
        self.assertFalse(report["foundation_passed"])
