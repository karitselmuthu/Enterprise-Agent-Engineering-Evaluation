"""Validated JSONL cases for answer evaluation."""

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class EvaluationCase:
    case_id: str
    question: str
    reference: str
    required_terms: tuple[str, ...] = ()
    evidence: str = ""


def load_cases(path: str | Path) -> list[EvaluationCase]:
    cases: list[EvaluationCase] = []
    seen: set[str] = set()
    with Path(path).open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
                if not isinstance(raw, dict):
                    raise ValueError("case must be an object")
                case_id, question, reference = (raw[key] for key in
                                                ("case_id", "question", "reference"))
                terms = raw.get("required_terms", [])
                evidence = raw.get("evidence", "")
                if (any(not isinstance(value, str) or not value.strip()
                        for value in (case_id, question, reference))
                        or not isinstance(terms, list)
                        or any(not isinstance(term, str) or not term.strip() for term in terms)
                        or not isinstance(evidence, str)):
                    raise ValueError("invalid case fields")
                if case_id in seen:
                    raise ValueError(f"duplicate case_id: {case_id}")
                seen.add(case_id)
                cases.append(EvaluationCase(case_id, question, reference,
                                            tuple(terms), evidence))
            except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
                raise ValueError(f"Invalid dataset line {line_number}: {exc}") from exc
    if not cases:
        raise ValueError("Dataset contains no cases")
    return cases
