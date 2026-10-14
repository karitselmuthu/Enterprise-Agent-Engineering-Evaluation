import unittest

from src.evaluation.biases import perturbation, position_swap
from src.evaluation.llm_judge import JudgeRequest, JudgeResult, OllamaPairwiseJudge


class BiasTests(unittest.TestCase):
    def test_position_swap_detects_first_position_preference(self):
        class AlwaysFirst:
            def choose(self, *args):
                return "A"
        result = position_swap(AlwaysFirst(), "q", "good", "bad", "good")
        self.assertFalse(result.consistent)

    def test_position_swap_accepts_consistent_choice(self):
        class SelectGood:
            def choose(self, question, a, b, reference):
                return "A" if a == reference else "B"
        self.assertTrue(position_swap(SelectGood(), "q", "good", "bad", "good").consistent)

    def test_perturbation_reports_direction(self):
        class LengthJudge:
            def evaluate(self, item):
                return JudgeResult(len(item.answer) / 100, "mock", "mock")
        case = JudgeRequest("q", "short", "short")
        self.assertGreater(perturbation(LengthJudge(), case, "much longer answer").score_change, 0)

    def test_pairwise_response_validation(self):
        judge = OllamaPairwiseJudge("model", post=lambda _: {
            "message": {"content": '{"winner":"C"}'}})
        with self.assertRaises(ValueError):
            judge.choose("q", "a", "b", "r")
