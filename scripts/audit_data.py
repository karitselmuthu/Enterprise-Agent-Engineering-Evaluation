"""Count committed data without treating scenario events as bulk datasets."""

import json
from pathlib import Path

from simulation.scenario_loader import load_scenarios


ROOT = Path(__file__).resolve().parents[1]


def audit_data(root: Path = ROOT) -> dict:
    scenarios = load_scenarios(root / "data/simulation/scenarios.jsonl")
    inventory_path = root / "data/synthetic/inventory.jsonl"
    inventory = ([json.loads(line) for line in inventory_path.read_text().splitlines()
                  if line.strip()] if inventory_path.exists() else [])
    metric_events = [(scenario, event) for scenario in scenarios.values()
                     for event in scenario.events if event["metrics"] is not None]
    log_events = [(scenario, event, log) for scenario in scenarios.values()
                  for event in scenario.events for log in event["logs"]]
    runbooks = sorted((root / "data/knowledge_base").glob("*.md"))
    fixture_incidents = sorted((root / "data/sample_incidents").glob("*.json"))
    audit = {
        "infrastructure_inventory": {
            "target": 50, "records": len(inventory),
            "distinct_server_ids_embedded_in_scenarios": len({
                scenario.incident["server_id"] for scenario in scenarios.values()}),
            "required_fields_complete": bool(inventory) and all(
                {"server_id", "environment", "application", "region"} <= item.keys()
                for item in inventory),
        },
        "infrastructure_metrics": {
            "target": 10000, "records": len(metric_events),
            "measurement_fields_complete": all(
                {"cpu_percent", "memory_percent", "disk_percent", "network_latency_ms"}
                <= event["metrics"].keys() for _, event in metric_events),
            "absolute_timestamp_present": all(
                "timestamp" in event["metrics"] for _, event in metric_events),
            "relative_minute_present": all(isinstance(event["minute"], int)
                                           for _, event in metric_events),
        },
        "application_logs": {
            "target": 20000, "records": len(log_events),
            "severity_and_message_present": all(
                {"severity", "message"} <= log.keys() for _, _, log in log_events),
            "service_linked_by_parent_scenario": all(
                bool(scenario.incident.get("service")) for scenario, _, _ in log_events),
            "absolute_timestamp_present": all("timestamp" in log
                                              for _, _, log in log_events),
            "relative_minute_present": all(isinstance(event["minute"], int)
                                           for _, event, _ in log_events),
        },
        "incident_records": {
            "target": 500, "simulated_alerts": len(scenarios),
            "separate_unit_fixtures": len(fixture_incidents),
            "severity_present": all("severity" in scenario.incident
                                    for scenario in scenarios.values()),
            "service_present": all(bool(scenario.incident.get("service"))
                                   for scenario in scenarios.values()),
            "status_derived_from_timeline": all(
                all("status" in event for event in scenario.events)
                for scenario in scenarios.values()),
        },
        "knowledge_base_documents": {
            "target": 50, "records": len(runbooks),
            "section_count": sum(sum(line.startswith("## ") for line in
                                     path.read_text(encoding="utf-8").splitlines())
                                 for path in runbooks),
        },
    }
    for category in audit.values():
        count = category.get("records", category.get("simulated_alerts", 0))
        category["volume_target_met"] = count >= category["target"]
    return audit


def main() -> None:
    print(json.dumps(audit_data(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
