"""Deterministic, order-independent checks for complete investigations.

These cues are deliberately narrow. A pass is grounded in visible tool output;
a failure can still be a valid paraphrase and needs human or judge review.
"""

import json
from statistics import mean

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import DEFAULT_SCENARIOS, load_scenarios
from src.agents.simulation_agent import SimulationInvestigator

from .simulation_eval import DEFAULT_TRUTH, load_ground_truth


# Source markers are checked in successful tool content, never in private labels.
# Action cues are checked only in the agent's final recommendation sentence.
CHECKS = {
    "SIM-001": ("Workers saturated", ("worker capacity", "cpu capacity")),
    "SIM-002": ("Out-of-memory restart", ("allocation", "memory leak")),
    "SIM-003": ("No space left on device", ("disk consumers", "free disk")),
    "SIM-004": ("pool exhaustion", ("connection pool", "database pool")),
    "SIM-005": ("Connection refused", ("database availability", "database endpoint")),
    "SIM-006": ("BackOff", ("pod events", "container restart")),
    "SIM-007": ("inventory-api", ("network path", "affected path")),
    "SIM-008": ("release deployed", ("rollback", "deployment")),
    "SIM-009": ("Authentication rejected", ("login", "authentication")),
    "SIM-010": ("Billing database connection refused", ("separate", "independently")),
    "SIM-011": (None, ("verify monitoring", "restore monitoring")),
    "SIM-012": ("Metrics endpoint timed out", ("unavailable", "retry")),
    "SIM-013": ("CPU saturation", ("another measurement", "verify monitoring")),
    "SIM-014": ("Service recovered", ("sustained recovery", "monitor")),
    "SIM-015": ("Latency alert repeated", ("same incident", "deduplicate")),
    "SIM-016": ("Metrics query forbidden", ("limited visibility", "unavailable")),
    "SIM-017": ("healthy", ("no active incident",)),
    "SIM-018": ("Cache backend unavailable", ("cache",)),
    "SIM-019": ("Consumer lag exceeded", ("consumer", "queue backlog")),
    "SIM-020": ("certificate expired", ("certificate",)),
    "SIM-021": ("NXDOMAIN", ("dns", "resolver")),
    "SIM-022": ("Read replica is 180", ("replica", "primary")),
    "SIM-023": ("Disk I/O wait", ("storage", "i/o")),
    "SIM-024": ("HTTP 429", ("quota", "request rate")),
    "SIM-025": ("eu-west-api", ("regional", "network path")),
}
EXPECTED_FAILURES = {"SIM-012": ("get_server_metrics", "timeout"),
                     "SIM-016": ("get_server_metrics", "permission_denied")}


def required_tools_selected(expected: list[str], selected: list[str]) -> bool:
    """Accept any valid investigation order and additional permitted calls."""
    return set(expected).issubset(selected)


def evaluate_scenarios(public_path=DEFAULT_SCENARIOS, truth_path=DEFAULT_TRUTH) -> dict:
    scenarios = load_scenarios(public_path)
    labels = load_ground_truth(truth_path)
    if set(scenarios) != set(labels) or set(scenarios) != set(CHECKS):
        raise ValueError("Scenario, label, and validation IDs differ")
    results = []
    for identifier in sorted(scenarios):
        label = labels[identifier]
        engine = ReplayEngine(scenarios[identifier], VirtualClock(label["evaluation_minute"]))
        state = SimulationInvestigator(replay_tools(engine)).run(identifier)
        selected = [event["tool"] for event in state.trace
                    if event.get("stage") == "selection"]
        marker, actions = CHECKS[identifier]
        visible = json.dumps([result.content for result in state.tool_results if result.ok],
                             sort_keys=True).casefold()
        failures = [(result.name, result.error_code) for result in state.tool_results
                    if not result.ok]
        expected_failure = EXPECTED_FAILURES.get(identifier)
        allowed_failures = [expected_failure] if expected_failure else []
        tool_selection = required_tools_selected(label["expected_tools"], selected)
        if identifier == "SIM-011":
            metrics = next(result for result in state.tool_results
                           if result.name == "get_server_metrics")
            logs = next(result for result in state.tool_results
                        if result.name == "get_application_logs")
            evidence = (metrics.ok and logs.ok and not metrics.content["samples"]
                        and not logs.content["entries"])
        else:
            evidence = (marker.casefold() in visible
                        and sorted(failures) == sorted(allowed_failures))
        # This is an intentionally conservative exact phrase check, not a
        # semantic claim that the causal explanation is correct.
        cause = (label["root_cause"].casefold() in state.answer.casefold() and evidence
                 if label["root_cause"] is not None else None)
        answer = state.answer.removesuffix(" Some observations were unavailable.")
        recommendation = answer.rsplit(". ", 1)[-1].strip(". ").casefold()
        action = any(cue.casefold() in recommendation for cue in actions)
        results.append({
            "scenario_id": identifier,
            "scenario_name": label["scenario_name"],
            "tool_selection": tool_selection,
            "evidence_retrieved": evidence,
            "root_cause_supported_proxy": cause,
            "recommendation_cue": action,
            "selected_tools": selected,
            "tool_failures": [{"name": name, "error_code": code} for name, code in failures],
            "answer": state.answer,
        })
    return {
        "scenario_count": len(results),
        "foundation_passed": all(item["tool_selection"] and item["evidence_retrieved"]
                                 for item in results),
        "tool_selection_rate": mean(float(item["tool_selection"]) for item in results),
        "evidence_retrieval_rate": mean(float(item["evidence_retrieved"]) for item in results),
        "root_cause_supported_proxy_rate": mean(
            float(item["root_cause_supported_proxy"]) for item in results
            if item["root_cause_supported_proxy"] is not None),
        "recommendation_cue_rate": mean(float(item["recommendation_cue"]) for item in results),
        "results": results,
    }
