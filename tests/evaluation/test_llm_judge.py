import json
import unittest

from src.evaluation.llm_judge import JudgeRequest, OllamaJudge


class JudgeTests(unittest.TestCase):
    def test_local_payload_and_valid_response(self):
        sent = []

        def post(payload):
            sent.append(payload)
            return {"message": {"content": json.dumps({
                "score": 0.75, "rationale": "Mostly supported by the evidence."
            })}}

        result = OllamaJudge("small-local-model", post=post).evaluate(
            JudgeRequest("question", "answer", "reference", "evidence"))
        self.assertEqual(result.score, 0.75)
        self.assertEqual(result.model, "small-local-model")
        self.assertEqual(sent[0]["options"]["temperature"], 0)
        self.assertEqual(sent[0]["format"]["required"], ["score", "rationale"])
        self.assertIn("evidence", sent[0]["messages"][1]["content"])

    def test_rejects_invalid_scores_and_rationale(self):
        for data in ({"score": 2, "rationale": "x"},
                     {"score": True, "rationale": "x"},
                     {"score": 0.5, "rationale": ""}):
            with self.subTest(data=data), self.assertRaises(ValueError):
                OllamaJudge("model", post=lambda _: {
                    "message": {"content": json.dumps(data)}}).evaluate(
                        JudgeRequest("q", "a", "r"))

    def test_rejects_malformed_response(self):
        with self.assertRaises(ValueError):
            OllamaJudge("model", post=lambda _: {"message": {"content": "no"}}).evaluate(
                JudgeRequest("q", "a", "r"))

    def test_transport_failure_is_visible(self):
        def fail(_):
            raise TimeoutError("local model unavailable")

        with self.assertRaisesRegex(TimeoutError, "unavailable"):
            OllamaJudge("model", post=fail).evaluate(JudgeRequest("q", "a", "r"))
