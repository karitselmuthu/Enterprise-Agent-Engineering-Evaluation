"""Define metric denominators without promoting proxies to semantic scores."""

from math import ceil, isfinite
from statistics import mean, median


def _fraction(numerator: int, denominator: int, scope: str) -> dict:
    if denominator <= 0 or not 0 <= numerator <= denominator:
        raise ValueError("Invalid metric numerator or denominator")
    return {"value": numerator / denominator, "numerator": numerator,
            "denominator": denominator, "unit": "fraction", "scope": scope,
            "status": "measured"}


def _unmeasured(reason: str) -> dict:
    return {"value": None, "status": "not_measured", "reason": reason}


def build_operational_metrics(scenarios: dict, reliability: dict) -> dict:
    cases = scenarios.get("results")
    count = scenarios.get("scenario_count")
    if not isinstance(cases, list) or not cases or count != len(cases):
        raise ValueError("Scenario report has an invalid case count")
    required = ("tool_selection", "evidence_retrieved", "root_cause_supported_proxy",
                "strict_completion_proxy", "attempted_tool_calls", "successful_tool_calls",
                "duration_ms")
    if any(not isinstance(case, dict) or any(field not in case for field in required)
           for case in cases):
        raise ValueError("Scenario report lacks required metric fields")
    if any(not isinstance(case["tool_selection"], bool)
           or not isinstance(case["evidence_retrieved"], bool)
           or not isinstance(case["strict_completion_proxy"], bool)
           or case["root_cause_supported_proxy"] is not None
           and not isinstance(case["root_cause_supported_proxy"], bool)
           or not isinstance(case["attempted_tool_calls"], int)
           or isinstance(case["attempted_tool_calls"], bool)
           or not isinstance(case["successful_tool_calls"], int)
           or isinstance(case["successful_tool_calls"], bool)
           or case["attempted_tool_calls"] < 0
           or not 0 <= case["successful_tool_calls"] <= case["attempted_tool_calls"]
           or not isinstance(case["duration_ms"], (int, float))
           or not isfinite(case["duration_ms"]) or case["duration_ms"] < 0
           for case in cases):
        raise ValueError("Scenario report has invalid call counts or durations")
    attempts = sum(case["attempted_tool_calls"] for case in cases)
    successes = sum(case["successful_tool_calls"] for case in cases)
    recovery_attempts = reliability.get("mcp_recovery_attempts")
    recovery_successes = reliability.get("mcp_recovery_successes")
    if (not isinstance(recovery_attempts, int) or isinstance(recovery_attempts, bool)
            or not isinstance(recovery_successes, int)
            or isinstance(recovery_successes, bool)
            or not 0 <= recovery_successes <= recovery_attempts):
        raise ValueError("Reliability report lacks valid recovery counts")
    durations = sorted(case["duration_ms"] for case in cases)
    causal = [case for case in cases if case["root_cause_supported_proxy"] is not None]
    selected = sum(bool(case["tool_selection"]) for case in cases)
    evidence = sum(bool(case["evidence_retrieved"]) for case in cases)
    completion_proxy = sum(bool(case["strict_completion_proxy"]) for case in cases)
    metrics = {
        "tool_selection_accuracy": _fraction(
            selected, count, "Required tool-name set per investigation; call order is free"),
        "tool_execution_success_rate": _fraction(
            successes, attempts, "Successful calls / all attempted calls, including expected faults"),
        "task_completion_rate": _unmeasured(
            "No validated human or semantic judgment of completed investigations"),
        "root_cause_identification_accuracy": _unmeasured(
            "Exact cause wording is not a validated diagnosis judgment"),
        "evidence_groundedness": _unmeasured(
            "Source availability does not verify every conclusion in the answer"),
        "hallucination_rate": _unmeasured(
            "No claim-level annotations or calibrated groundedness judge"),
        "recovery_success_rate": _fraction(
            recovery_successes, recovery_attempts,
            "Successful recovery after one injected temporary MCP outage"),
        "average_tool_calls": {"value": attempts / count, "numerator": attempts,
                               "denominator": count, "unit": "calls per investigation",
                               "scope": "All scenario agent tool invocations", "status": "measured"},
        "end_to_end_latency": {"value": mean(durations), "unit": "milliseconds",
                               "median_ms": median(durations),
                               "p95_ms": durations[ceil(0.95 * count) - 1],
                               "scope": "Scenario dispatch through answer on local mock backend; "
                                        "excludes dataset loading and report writing",
                               "status": "measured"},
        "token_consumption": _unmeasured(
            "The deterministic simulation agent makes no LLM calls and emits no token usage"),
    }
    metrics["recovery_success_rate"]["status"] = "measured_small_sample"
    return {"scenario_count": count, "metrics": metrics,
            "diagnostics": {
                "source_evidence_available": _fraction(
                    evidence, count, "Required source marker or expected evidence gap"),
                "strict_completion_proxy": _fraction(
                    completion_proxy, count,
                    "All deterministic tool, evidence, exact-cause, and recommendation cues"),
                "exact_cause_phrase_proxy": (_fraction(
                    sum(bool(case["root_cause_supported_proxy"]) for case in causal),
                    len(causal), "Exact private cause phrase in grounded answer")
                    if causal else _unmeasured("No causal scenarios")),
            }}
