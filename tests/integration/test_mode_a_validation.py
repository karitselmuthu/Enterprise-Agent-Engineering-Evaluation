"""Validate time-bounded evidence and changing investigation advice."""

import unittest

from src.evaluation.replay_validation import capture_replay, validate_mode_a


class ModeAValidationTests(unittest.TestCase):
    def test_eight_point_replay_passes(self):
        report = validate_mode_a()
        self.assertTrue(report["passed"], report["checks"])
        self.assertTrue(all(report["checks"].values()))

    def test_early_investigation_cannot_see_failure_or_recovery(self):
        before_alert = capture_replay("SIM-004", 5)
        self.assertEqual(before_alert["status"], "not_raised")
        early = capture_replay("SIM-004", 15)
        self.assertEqual(early["observed_at"], "2026-10-14T10:15:00Z")
        self.assertEqual(early["visible_metric_minutes"], [0, 5, 10, 15])
        self.assertNotIn("pool exhausted", early["answer"].lower())
        self.assertNotIn("Service recovered", early["answer"])

    def test_later_investigation_changes_recommendation(self):
        early = capture_replay("SIM-004", 15)
        later = capture_replay("SIM-004", 25)
        self.assertEqual(later["observed_at"], "2026-10-14T10:25:00Z")
        self.assertEqual(later["latest_log"]["severity"], "ERROR")
        self.assertIn("Escalate active failures", later["answer"])
        self.assertNotEqual(early["answer"], later["answer"])
