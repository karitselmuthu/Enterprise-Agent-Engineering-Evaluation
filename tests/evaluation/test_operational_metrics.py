"""Metric denominators, unavailable scores, and malformed input handling."""

import copy
import unittest

from src.evaluation.operational_metrics import build_operational_metrics
from src.evaluation.scenario_validation import evaluate_scenarios


class OperationalMetricTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = evaluate_scenarios()
        cls.reliability = {"mcp_recovery_attempts": 1, "mcp_recovery_successes": 1}

    def test_metric_denominators_and_unmeasured_fields(self):
        report = build_operational_metrics(self.scenarios, self.reliability)
        metrics = report["metrics"]
        self.assertEqual(len(metrics), 10)
        self.assertEqual(metrics["tool_selection_accuracy"]["numerator"], 25)
        self.assertEqual(metrics["tool_selection_accuracy"]["denominator"], 25)
        self.assertEqual(metrics["tool_execution_success_rate"]["numerator"], 78)
        self.assertEqual(metrics["tool_execution_success_rate"]["denominator"], 80)
        self.assertEqual(metrics["average_tool_calls"]["value"], 3.2)
        self.assertEqual(metrics["recovery_success_rate"]["denominator"], 1)
        self.assertEqual(report["diagnostics"]["strict_completion_proxy"]["numerator"], 3)
        for name in ("task_completion_rate", "root_cause_identification_accuracy",
                     "evidence_groundedness", "hallucination_rate", "token_consumption"):
            self.assertIsNone(metrics[name]["value"])
            self.assertEqual(metrics[name]["status"], "not_measured")
        latency = metrics["end_to_end_latency"]
        self.assertGreaterEqual(latency["value"], 0)
        self.assertGreaterEqual(latency["p95_ms"], latency["median_ms"])

    def test_invalid_inputs_do_not_create_false_scores(self):
        bad = copy.deepcopy(self.scenarios)
        bad["results"][0]["successful_tool_calls"] = 100
        with self.assertRaises(ValueError):
            build_operational_metrics(bad, self.reliability)
        bad = copy.deepcopy(self.scenarios)
        bad["results"][0]["duration_ms"] = float("nan")
        with self.assertRaises(ValueError):
            build_operational_metrics(bad, self.reliability)
        bad = copy.deepcopy(self.scenarios)
        bad["results"][0]["tool_selection"] = "yes"
        with self.assertRaises(ValueError):
            build_operational_metrics(bad, self.reliability)
        with self.assertRaises(ValueError):
            build_operational_metrics(self.scenarios,
                                      {"mcp_recovery_attempts": 0,
                                       "mcp_recovery_successes": 0})
