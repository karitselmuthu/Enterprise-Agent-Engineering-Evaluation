"""Public, deterministic fault variants for one replay scenario."""

from copy import deepcopy

from .scenario_loader import Scenario


def database_latency_variants(base: Scenario, evaluation_minute: int = 25) -> dict[str, Scenario]:
    if not base.incident.get("database_id"):
        raise ValueError("Scenario has no database observation contract")
    variants = {"baseline": base}
    for name in ("missing_metrics", "tool_timeout", "misleading_logs"):
        events = deepcopy(list(base.events))
        if name == "missing_metrics":
            for event in events:
                event["database_metrics"] = None
        elif name == "tool_timeout":
            target = next((event for event in events
                           if event["minute"] == evaluation_minute), None)
            if target is None:
                raise ValueError("Evaluation minute absent from scenario timeline")
            target["faults"].append("get_database_metrics")
        else:
            for event in events:
                if event["minute"] >= 10:
                    event["logs"] = [{"timestamp": event["timestamp"], "severity": "WARN",
                                      "message": "Network congestion suspected; database pool healthy"}]
        variants[name] = Scenario(base.scenario_id, deepcopy(base.incident),
                                  tuple(events), base.allowed_tools)
    return variants
