"""Score fixed answer pairs with deterministic metrics and an optional judge."""

from dataclasses import asdict, dataclass
from statistics import mean
from typing import Protocol

from .datasets import EvaluationCase
from .llm_judge import JudgeRequest, JudgeResult
from .metrics import exact_match, required_term_recall, token_f1


class Judge(Protocol):
    def evaluate(self, item: JudgeRequest) -> JudgeResult: ...


@dataclass(frozen=True)
class CaseScore:
    case_id: str
    exact_match: float
    token_f1: float
    required_term_recall: float
    judge_score: float | None = None
    judge_rationale: str | None = None


def evaluate_answers(cases: list[EvaluationCase], answers: dict[str, str],
                     judge: Judge | None = None) -> dict:
    if not cases:
        raise ValueError("At least one case is required")
    expected_ids = {case.case_id for case in cases}
    if set(answers) != expected_ids or any(not isinstance(value, str) for value in answers.values()):
        raise ValueError("Answers must contain exactly one string per case")
    scores: list[CaseScore] = []
    for case in cases:
        answer = answers[case.case_id]
        judgment = (judge.evaluate(JudgeRequest(case.question, answer, case.reference,
                                                case.evidence)) if judge else None)
        scores.append(CaseScore(
            case.case_id, exact_match(answer, case.reference), token_f1(answer, case.reference),
            required_term_recall(answer, case.required_terms),
            judgment.score if judgment else None,
            judgment.rationale if judgment else None,
        ))
    result = {
        "case_count": len(scores),
        "cases": [asdict(score) for score in scores],
        "mean_exact_match": mean(score.exact_match for score in scores),
        "mean_token_f1": mean(score.token_f1 for score in scores),
        "mean_required_term_recall": mean(score.required_term_recall for score in scores),
    }
    if judge:
        result["mean_judge_score"] = mean(score.judge_score for score in scores)
    return result
