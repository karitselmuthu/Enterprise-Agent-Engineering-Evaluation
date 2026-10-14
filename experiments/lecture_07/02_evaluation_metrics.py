"""Offline deterministic evaluation of fixed answer pairs."""

import json
from pathlib import Path
from src.evaluation.datasets import load_cases
from src.evaluation.runner import evaluate_answers


if __name__ == "__main__":
    path = Path("data/evaluation_datasets/answer_cases.jsonl")
    cases = load_cases(path)
    answers = {case.case_id: case.reference for case in cases}
    print(json.dumps(evaluate_answers(cases, answers), indent=2))
