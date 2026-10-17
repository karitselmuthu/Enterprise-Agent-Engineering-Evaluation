"""Score the database-latency workflow against private, deterministic expectations."""

from statistics import mean

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.faults import database_latency_variants
from simulation.scenario_loader import DEFAULT_SCENARIOS, load_scenarios
from src.agents.simulation_agent import SimulationInvestigator

from .process_validation import inspect_process
from .simulation_eval import DEFAULT_TRUTH, load_ground_truth


EXPECTED = {
    "baseline": ("supported_hypothesis", True, False, "SUCCESS"),
    "missing_metrics": ("insufficient_evidence", False, False, "SUCCESS"),
    "tool_timeout": ("insufficient_evidence", False, False, "TIMEOUT"),
    "misleading_logs": ("supported_hypothesis", True, True, "SUCCESS"),
}


def evaluate_database_latency(public_path=DEFAULT_SCENARIOS,
                              truth_path=DEFAULT_TRUTH) -> dict:
    base = load_scenarios(public_path)["SIM-004"]
    label = load_ground_truth(truth_path)["SIM-004"]
    minute = label["evaluation_minute"]
    expected_cause = label["root_cause"].casefold()
    results = []

    def event_index(events: list[dict], kind: str, tool: str | None = None) -> int | None:
        return next((index for index, event in enumerate(events)
                     if event["kind"] == kind and
                     (tool is None or event.get("tool") == tool)), None)

    for variant, scenario in database_latency_variants(base, minute).items():
        state = SimulationInvestigator(replay_tools(
            ReplayEngine(scenario, VirtualClock(minute)))).run(scenario.scenario_id)
        expected_status, expected_db_card, expected_conflict, expected_tool_status = EXPECTED[variant]
        events = state.investigation.events
        database_call = next((result for result in state.tool_results
                              if result.name == "get_database_metrics"), None)
        database_cards = [card for card in state.evidence_cards
                          if card.signal == "database_connection_pool"]
        hypothesis_check = next((event for event in events
                                 if event["kind"] == "hypothesis_verified"), None)
        selected = [event["tool"] for event in state.trace
                    if event.get("stage") == "selection"]
        latency_at = event_index(events, "latency_detected")
        database_at = event_index(events, "tool_proposed", "get_database_metrics")
        checks = {
            "investigation_started": any(event["kind"] == "investigation_started"
                                         for event in events),
            "observation_tools_selected": {"get_incident_record", "get_server_metrics",
                                           "get_application_logs"} <= set(selected),
            "latency_observed_before_database_call": (latency_at is not None and
                database_at is not None and latency_at < database_at),
            "authorized_database_tool": ("get_database_metrics" in selected and
                any(event["kind"] == "policy_checked"
                    and event.get("tool") == "get_database_metrics"
                    and event["allowed"] for event in events)),
            "database_tool_status": bool(database_call) and
                database_call.status.value == expected_tool_status,
            "database_evidence_expected": bool(database_cards) == expected_db_card,
            "hypothesis_outcome": bool(state.finding) and
                state.finding.status == expected_status and
                (state.finding.hypothesis == expected_cause
                 if expected_status == "supported_hypothesis"
                 else state.finding.hypothesis is None),
            "support_checked": bool(hypothesis_check) and
                hypothesis_check["supported"] == expected_db_card and
                hypothesis_check["conflicting_log"] == expected_conflict,
            "evidence_citations": inspect_process(state)["citation_integrity"],
            "lifecycle": inspect_process(state)["trajectory_valid"],
        }
        score = sum(checks.values()) / len(checks)
        results.append({"variant": variant, "passed": all(checks.values()),
                        "score": score,
                        "checks": checks,
                        "finding_status": state.finding.status if state.finding else None,
                        "hypothesis": state.finding.hypothesis if state.finding else None,
                        "tool_calls": selected,
                        "database_tool_status": database_call.status.value if database_call else None,
                        "evidence_ids": [card.evidence_id for card in state.evidence_cards],
                        "answer": state.answer})
    return {"scenario_id": "SIM-004", "evaluation_minute": minute,
            "variant_count": len(results), "passed": all(item["passed"] for item in results),
            "mean_workflow_score": mean(item["score"] for item in results),
            "results": results,
            "scope": "Deterministic simulated workflow and evidence checks; likely cause "
                     "remains a hypothesis, not verified production RCA"}
