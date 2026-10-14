import tempfile
import unittest
from pathlib import Path

from src.agents.state import AgentState
from src.evaluation.benchmarks import load_benchmark, run_benchmark
from src.evaluation.reports import write_report


DATASET = "data/evaluation_datasets/incident_benchmark.jsonl"


class BenchmarkTests(unittest.TestCase):
    def test_mock_benchmark_passes_and_is_reproducible(self):
        cases, fingerprint = load_benchmark(DATASET)
        first = run_benchmark(cases, fingerprint)
        second = run_benchmark(cases, fingerprint)
        self.assertEqual(first, second)
        self.assertTrue(first["passed"])
        self.assertEqual(first["case_count"], 3)
        self.assertEqual(first["mean_trajectory_accuracy"], 1)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            write_report(output, first)
            self.assertIn(fingerprint, output.read_text())

    def test_bad_agent_fails_gate(self):
        cases, fingerprint = load_benchmark(DATASET)
        report = run_benchmark(cases, fingerprint, lambda request: AgentState(request))
        self.assertFalse(report["passed"])
        self.assertEqual(report["mean_trajectory_accuracy"], 0)

    def test_invalid_dataset_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text('{"case_id":"x"}\n')
            with self.assertRaisesRegex(ValueError, "line 1"):
                load_benchmark(path)
