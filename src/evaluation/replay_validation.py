"""Acceptance checks for the eight-point database incident replay."""

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import load_scenarios
from src.agents.simulation_agent import SimulationInvestigator


def capture_replay(scenario_id: str, minute: int) -> dict:
    scenario = load_scenarios()[scenario_id]
    engine = ReplayEngine(scenario, VirtualClock(minute))
    state = SimulationInvestigator(replay_tools(engine)).run(scenario_id)
    results = {result.name: result for result in state.tool_results}
    if not results["get_incident_record"].ok:
        return {"scenario_id": scenario_id, "minute": minute,
                "observed_at": engine.observed_at(), "status": "not_raised",
                "tool_error": results["get_incident_record"].error,
                "selected_tools": ["get_incident_record"], "answer": state.answer}
    incident = results["get_incident_record"].content
    metrics = results["get_server_metrics"].content
    logs = results["get_application_logs"].content
    return {
        "scenario_id": scenario_id,
        "minute": minute,
        "observed_at": incident["observed_at"],
        "status": incident["status"],
        "latest_metrics": metrics["samples"][-1] if metrics["samples"] else None,
        "latest_log": logs["entries"][-1] if logs["entries"] else None,
        "visible_metric_minutes": [sample["minute"] for sample in metrics["samples"]],
        "visible_log_minutes": [entry["minute"] for entry in logs["entries"]],
        "selected_tools": [event["tool"] for event in state.trace
                           if event.get("stage") == "selection"],
        "answer": state.answer,
    }


def validate_mode_a() -> dict:
    timeline = [event["minute"] for event in load_scenarios()["SIM-004"].events]
    early = capture_replay("SIM-004", 15)
    failure = capture_replay("SIM-004", 25)
    recovered = capture_replay("SIM-004", 35)
    snapshots = [early, failure, recovered]
    checks = {
        "eight_ordered_events": timeline == list(range(0, 40, 5)),
        "no_alert_before_1010": capture_replay("SIM-004", 5)["status"] == "not_raised",
        "no_future_observations": all(
            all(value <= snapshot["minute"] for value in
                snapshot["visible_metric_minutes"] + snapshot["visible_log_minutes"])
            for snapshot in snapshots),
        "warning_at_1015": (early["latest_metrics"]["cpu_percent"] == 82
                            and early["latest_metrics"]["memory_percent"] == 73
                            and early["latest_log"]["severity"] == "WARN"
                            and "Check the warning trend" in early["answer"]),
        "failure_at_1025": (failure["latest_metrics"]["cpu_percent"] == 97
                            and failure["latest_metrics"]["memory_percent"] == 89
                            and failure["latest_log"]["severity"] == "ERROR"
                            and "Escalate active failures" in failure["answer"]),
        "recovered_at_1035": (recovered["status"] == "resolved"
                              and recovered["latest_metrics"]["cpu_percent"] == 43
                              and "Confirm sustained recovery" in recovered["answer"]),
        "evidence_and_recommendation_change": early["answer"] != failure["answer"]
                                              and failure["answer"] != recovered["answer"],
        "replay_is_deterministic": capture_replay("SIM-004", 25) == failure,
    }
    return {"scenario_id": "SIM-004", "passed": all(checks.values()),
            "checks": checks, "snapshots": snapshots}
