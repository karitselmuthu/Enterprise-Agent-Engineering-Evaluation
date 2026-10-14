"""Controlled probes for judge sensitivity and order effects."""

from dataclasses import dataclass
from typing import Protocol

from .llm_judge import JudgeRequest, JudgeResult


class PairwiseJudge(Protocol):
    def choose(self, question: str, candidate_a: str, candidate_b: str,
               reference: str) -> str: ...


class ScoringJudge(Protocol):
    def evaluate(self, item: JudgeRequest) -> JudgeResult: ...


@dataclass(frozen=True)
class PositionProbe:
    first_winner: str
    swapped_winner: str
    consistent: bool


def position_swap(judge: PairwiseJudge, question: str, answer_a: str,
                  answer_b: str, reference: str) -> PositionProbe:
    first = judge.choose(question, answer_a, answer_b, reference)
    second = judge.choose(question, answer_b, answer_a, reference)
    if first not in {"A", "B", "tie"} or second not in {"A", "B", "tie"}:
        raise ValueError("Pairwise judge returned an unknown winner")
    mapping = {"A": "B", "B": "A", "tie": "tie"}
    return PositionProbe(first, second, mapping[first] == second)


@dataclass(frozen=True)
class SensitivityProbe:
    baseline_score: float
    perturbed_score: float
    score_change: float


def perturbation(judge: ScoringJudge, case: JudgeRequest,
                 modified_answer: str) -> SensitivityProbe:
    baseline = judge.evaluate(case).score
    changed = judge.evaluate(JudgeRequest(case.question, modified_answer,
                                          case.reference, case.evidence)).score
    return SensitivityProbe(baseline, changed, changed - baseline)
