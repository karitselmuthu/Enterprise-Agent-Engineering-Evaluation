"""Operational workload and failure recovery checks."""

import unittest

from src.evaluation.reliability import run_bounded_investigation, run_reliability_workload


class ReliabilityTests(unittest.TestCase):
    def test_initial_workload_passes(self):
        report = run_reliability_workload(concurrent=10, sequential=50)
        self.assertTrue(report["passed"], report["checks"])
        self.assertEqual(report["concurrent_count"], 10)
        self.assertEqual(report["peak_in_flight"], 10)
        self.assertEqual(report["sequential_count"], 50)
        self.assertEqual(report["repeated_count"], 5)

    def test_bounded_agent_can_complete_and_be_stopped(self):
        completed = run_bounded_investigation("SIM-001", 10, 0, 2)
        self.assertEqual(completed["status"], "completed", completed)
        timed = run_bounded_investigation("SIM-001", 10, 0.3, 0.03)
        self.assertEqual(timed["status"], "timed_out", timed)

    def test_invalid_workload_configuration(self):
        with self.assertRaises(ValueError):
            run_reliability_workload(concurrent=1)
        with self.assertRaises(ValueError):
            run_reliability_workload(sequential=0)
        with self.assertRaises(ValueError):
            run_bounded_investigation("SIM-001", 10, 0, 0)
