import tempfile
import unittest
from pathlib import Path

from src.evaluation.datasets import EvaluationCase, load_cases
from src.evaluation.llm_judge import JudgeResult
from src.evaluation.metrics import exact_match, required_term_recall, token_f1
from src.evaluation.runner import evaluate_answers


class MetricsTests(unittest.TestCase):
    def test_metric_edges(self):
        self.assertEqual(exact_match("The service is DOWN!", "the service is down"), 1)
        self.assertEqual(token_f1("", "reference"), 0)
        self.assertAlmostEqual(token_f1("a b", "a c"), 0.5)
        self.assertEqual(required_term_recall("pool exhaustion seen", ("pool exhaustion", "cpu")), 0.5)

    def test_dataset_validation(self):
        cases = load_cases("data/evaluation_datasets/answer_cases.jsonl")
        self.assertEqual(len(cases), 2)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.jsonl"
            path.write_text('{"case_id":"x","question":"q","reference":"r"}\n'
                            '{"case_id":"x","question":"q","reference":"r"}\n')
            with self.assertRaisesRegex(ValueError, "duplicate"):
                load_cases(path)

    def test_runner_aggregates_and_checks_ids(self):
        cases = [EvaluationCase("one", "q", "right", ("right",))]

        class FakeJudge:
            def evaluate(self, item):
                self_item = item
                assert self_item.answer == "right"
                return JudgeResult(0.8, "supported", "fake")

        result = evaluate_answers(cases, {"one": "right"}, FakeJudge())
        self.assertEqual(result["mean_exact_match"], 1)
        self.assertEqual(result["mean_judge_score"], 0.8)
        with self.assertRaises(ValueError):
            evaluate_answers(cases, {"wrong": "right"})
