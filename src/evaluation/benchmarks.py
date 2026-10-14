"""Versioned, deterministic benchmark for the fixture-backed mock agent."""

from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from statistics import mean
from typing import Callable

from src.agents.runtime import IncidentAgent
from src.agents.state import AgentState
from .agent_evaluator import AgentCase, ExpectedCall, evaluate_agent_state


BENCHMARK_VERSION = "incident-agent-v1"


@dataclass(frozen=True)
class BenchmarkCase:
    agent_case: AgentCase


def load_benchmark(path: str | Path) -> tuple[list[BenchmarkCase], str]:
    raw_bytes = Path(path).read_bytes()
    fingerprint = sha256(raw_bytes).hexdigest()
    cases: list[BenchmarkCase] = []
    seen: set[str] = set()
    for number, line in enumerate(raw_bytes.decode("utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            case_id = item["case_id"]
            request = item["request"]
            calls = item["expected_calls"]
            terms = item["answer_terms"]
            if (not isinstance(case_id, str) or not case_id.strip()
                    or case_id in seen or not isinstance(request, str) or not request.strip()
                    or not isinstance(calls, list) or not isinstance(terms, list)
                    or any(not isinstance(call, dict) or not isinstance(call.get("name"), str)
                           or not call["name"] or not isinstance(call.get("arguments"), dict)
                           for call in calls)
                    or any(not isinstance(term, str) or not term.strip() for term in terms)):
                raise ValueError("invalid or duplicate case fields")
            seen.add(case_id)
            cases.append(BenchmarkCase(AgentCase(case_id, request,
                tuple(ExpectedCall(call["name"], call["arguments"]) for call in calls),
                tuple(terms))))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid benchmark line {number}: {exc}") from exc
    if not cases:
        raise ValueError("Benchmark contains no cases")
    return cases, fingerprint


def run_benchmark(cases: list[BenchmarkCase], dataset_sha256: str,
                  run_agent: Callable[[str], AgentState] | None = None) -> dict:
    if not cases:
        raise ValueError("At least one benchmark case is required")
    agent = run_agent or IncidentAgent().run
    results = [evaluate_agent_state(case.agent_case, agent(case.agent_case.request))
               for case in cases]
    selection = mean(float(result["tool_selection_correct"]) for result in results)
    trajectory = mean(float(result["trajectory_exact"]) for result in results)
    success = mean(float(result["execution_success"]) for result in results)
    recall = mean(result["answer_term_recall"] for result in results)
    passed = all(result["trajectory_exact"] and result["execution_success"]
                 and result["answer_term_recall"] == 1
                 and not result["permission_violation"] for result in results)
    return {
        "benchmark_version": BENCHMARK_VERSION,
        "backend": "mock" if run_agent is None else "custom",
        "dataset_sha256": dataset_sha256,
        "case_count": len(results),
        "mean_tool_selection_accuracy": selection,
        "mean_trajectory_accuracy": trajectory,
        "mean_execution_success": success,
        "mean_answer_term_recall": recall,
        "passed": passed,
        "cases": results,
    }
