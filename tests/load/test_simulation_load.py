"""Concurrent tool reads use consistent immutable virtual-time snapshots."""

import unittest

from src.evaluation.synthetic_load import validate_synthetic_load


class SimulationLoadTests(unittest.TestCase):
    def test_ten_concurrent_and_fifty_sequential_reads(self):
        report = validate_synthetic_load()
        self.assertTrue(report["passed"])
        self.assertEqual(report["concurrent_successes"], 10)
        self.assertEqual(report["sequential_successes"], 50)

    def test_invalid_workload_rejected(self):
        with self.assertRaises(ValueError):
            validate_synthetic_load(concurrent=0)


if __name__ == "__main__":
    unittest.main()
