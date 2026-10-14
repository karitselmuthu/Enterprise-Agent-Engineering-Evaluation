"""Exercise dataset, optional judge, scoring, and report output together."""

import json
import tempfile
import unittest
from pathlib import Path

from src.evaluation.datasets import load_cases
from src.evaluation.llm_judge import OllamaJudge
from src.evaluation.reports import write_report
from src.evaluation.runner import evaluate_answers


class AnswerEvaluationPipelineTests(unittest.TestCase):
    def test_fixture_cases_flow_through_judge_and_report(self):
        cases = load_cases("data/evaluation_datasets/answer_cases.jsonl")
        answers = {case.case_id: case.reference for case in cases}
        judge = OllamaJudge("fixture-model", post=lambda _: {
            "message": {"content": json.dumps({"score": 1, "rationale": "Supported"})}})
        report = evaluate_answers(cases, answers, judge)
        self.assertEqual(report["case_count"], 2)
        self.assertEqual(report["mean_exact_match"], 1)
        self.assertEqual(report["mean_judge_score"], 1)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "evaluation.json"
            write_report(path, report)
            self.assertEqual(json.loads(path.read_text()), report)

    def test_invalid_judge_output_stops_report_generation(self):
        cases = load_cases("data/evaluation_datasets/answer_cases.jsonl")
        answers = {case.case_id: case.reference for case in cases}
        judge = OllamaJudge("fixture-model", post=lambda _: {
            "message": {"content": '{"score":2,"rationale":"invalid"}'}})
        with self.assertRaisesRegex(ValueError, "score"):
            evaluate_answers(cases, answers, judge)
