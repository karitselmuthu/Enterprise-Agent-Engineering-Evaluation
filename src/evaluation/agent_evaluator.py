"""Evaluate agent tool choices, execution trace, and final answer."""

from dataclasses import dataclass
from typing import Any

from src.agents.state import AgentState
from .metrics import required_term_recall


@dataclass(frozen=True)
class ExpectedCall:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class AgentCase:
    case_id: str
    request: str
    expected_calls: tuple[ExpectedCall, ...]
    answer_terms: tuple[str, ...]


def evaluate_agent_state(case: AgentCase, state: AgentState) -> dict:
    selections = [event for event in state.trace
                  if event.get("stage") == "selection" and event.get("tool")]
    actual = [(event["tool"], event.get("arguments", {})) for event in selections]
    expected = [(call.name, call.arguments) for call in case.expected_calls]
    execution = [event for event in state.trace if event.get("stage") == "execution"]
    denied = any(event.get("error_code") == "permission_denied" for event in execution)
    failures = [result.error_code for result in state.tool_results if not result.ok]
    return {
        "case_id": case.case_id,
        "tool_selection_correct": bool(actual) and actual[0] == expected[0] if expected else not actual,
        "trajectory_exact": actual == expected,
        "execution_success": len(state.tool_results) == len(expected)
        and all(result.ok for result in state.tool_results),
        "permission_violation": denied,
        "tool_failures": failures,
        "answer_term_recall": required_term_recall(state.answer, case.answer_terms),
        "selected_calls": [{"name": name, "arguments": arguments}
                           for name, arguments in actual],
    }
