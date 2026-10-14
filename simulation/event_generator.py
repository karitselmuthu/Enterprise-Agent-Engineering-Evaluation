"""Offline fixture generator. Runtime replay never imports this module."""

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "data/simulation/scenarios.jsonl"
TRUTH = ROOT / "data/evaluation_datasets/simulation_ground_truth.jsonl"

# ID, alert summary, cause label, warning, incident log, metric profile, behavior.
SPECS = [
    ("SIM-001", "API latency rising", "CPU saturation", "Worker CPU queue growing", "Workers saturated; requests delayed", "cpu", "degraded"),
    ("SIM-002", "API memory pressure", "Memory leak", "Resident memory increasing", "Out-of-memory restart after growth", "memory", "degraded"),
    ("SIM-003", "Writes failing", "Disk exhaustion", "Disk free space declining", "No space left on device", "disk", "degraded"),
    ("SIM-004", "Payment requests slow", "Database connection pool exhaustion", "Database connections near pool limit", "Connection pool exhausted; requests waiting", "database", "degraded"),
    ("SIM-005", "Database requests failing", "Database unavailable", "Database health checks intermittent", "Connection refused by database endpoint", "normal", "degraded"),
    ("SIM-006", "Pods restarting", "Kubernetes pod crash loop", "Pod restart count increasing", "Container exited repeatedly after startup", "memory", "degraded"),
    ("SIM-007", "Checkout latency high", "Network latency", "Cross-zone round trip increasing", "Upstream requests timed out over network", "network", "degraded"),
    ("SIM-008", "Errors after release", "Deployment regression", "New release deployed at minute 5", "Errors increased immediately after deployment", "normal", "degraded"),
    ("SIM-009", "Login failures", "Authentication failures", "Failed login count rising", "Authentication rejected for many users", "normal", "degraded"),
    ("SIM-010", "Two alerts on one host", "Concurrent CPU and database incidents", "Worker CPU high; database retries observed", "CPU queue saturated and database connection refused", "cpu", "degraded"),
    ("SIM-011", "Monitoring gap", "Unknown due to missing telemetry", "Metric collector has no new samples", "No application diagnostic event available", "missing", "missing"),
    ("SIM-012", "Metrics query unreliable", "Metrics tool timeout", "Metrics endpoint response slowing", "Metrics endpoint timed out during investigation", "normal", "timeout"),
    ("SIM-013", "Signals conflict", "Conflicting monitoring evidence", "Dashboard reports normal CPU", "Worker reports CPU saturation despite normal dashboard", "normal", "conflict"),
    ("SIM-014", "Service recovering", "Recovery after CPU saturation", "Worker queue shrinking", "Request latency returning to baseline", "recovery", "recovery"),
    ("SIM-015", "Repeated latency alerts", "Repeated alerts for same incident", "Latency alert repeated", "Latency alert repeated; no new failure mode", "network", "repeat"),
    ("SIM-016", "Operator access restricted", "Permission denied on metrics", "Metrics access policy changed", "Metrics query forbidden to operator", "normal", "permission"),
    ("SIM-017", "No active issue", "Healthy infrastructure", "Routine health check passed", "No errors observed", "normal", "healthy"),
    ("SIM-018", "Cache miss surge", "Cache outage", "Cache hit ratio falling", "Cache backend unavailable; database load rising", "database", "degraded"),
    ("SIM-019", "Queue processing delayed", "Message queue backlog", "Queue depth increasing", "Consumer lag exceeded threshold", "cpu", "degraded"),
    ("SIM-020", "API certificate errors", "Expired TLS certificate", "Certificate expiry approaching", "TLS handshake rejected: certificate expired", "normal", "degraded"),
]

PROFILES = {
    "cpu": [(35, 48, 45, 20), (67, 55, 47, 45), (95, 64, 48, 180), (97, 69, 49, 220)],
    "memory": [(30, 48, 45, 20), (39, 72, 46, 30), (51, 91, 46, 90), (64, 98, 47, 160)],
    "disk": [(31, 50, 60, 20), (34, 51, 82, 25), (40, 53, 97, 100), (42, 54, 99, 140)],
    "database": [(34, 48, 44, 20), (44, 57, 45, 65), (70, 71, 45, 180), (79, 78, 46, 230)],
    "network": [(33, 49, 45, 20), (39, 51, 45, 105), (47, 54, 45, 240), (50, 56, 45, 300)],
    "normal": [(34, 48, 45, 20), (36, 49, 45, 21), (35, 50, 45, 20), (34, 50, 45, 19)],
    "recovery": [(35, 48, 45, 20), (78, 58, 45, 100), (95, 65, 46, 190), (39, 52, 46, 24)],
    "missing": [None, None, None, None],
}

SERVICES = (
    "checkout-api", "catalog-api", "order-writer", "payment-service", "billing-api",
    "inventory-worker", "checkout-edge", "fulfillment-api", "identity-service",
    "payment-gateway", "analytics-api", "telemetry-api", "search-api",
    "notification-worker", "edge-router", "admin-api", "health-service",
    "recommendation-api", "order-queue", "customer-portal",
)


def build_records() -> tuple[list[dict], list[dict]]:
    public, truth = [], []
    for index, (scenario_id, summary, cause, warning, error, profile, behavior) in enumerate(SPECS, 1):
        service = SERVICES[index - 1]
        server_id = f"prod-app-{index:03d}"
        events = []
        for offset, minute in enumerate((0, 5, 10, 15)):
            reading = PROFILES[profile][offset]
            metrics = (None if reading is None else dict(zip(
                ("cpu_percent", "memory_percent", "disk_percent", "network_latency_ms"),
                reading)))
            if offset == 0:
                message, severity = "Routine baseline observation", "INFO"
            elif offset == 1:
                message, severity = warning, "WARN"
            elif offset == 2:
                message, severity = error, "INFO" if behavior == "healthy" else "ERROR"
            else:
                message, severity = ("Service recovered" if behavior == "recovery" else error), (
                    "INFO" if behavior in {"recovery", "healthy"} else "ERROR")
            logs = [{"severity": severity, "message": message}]
            if behavior == "repeat" and minute >= 10:
                logs.append({"severity": "WARN", "message": warning})
            if behavior == "missing":
                logs = []
            status = ("healthy" if behavior == "healthy" else
                      "resolved" if behavior == "recovery" and minute == 15 else
                      "open" if minute == 0 else "degraded")
            events.append({"minute": minute, "metrics": metrics, "logs": logs,
                           "status": status,
                           "faults": ["get_server_metrics"] if behavior == "timeout" and minute == 10 else []})
        public.append({"scenario_id": scenario_id,
                       "incident": {"id": scenario_id, "server_id": server_id,
                                    "service": service, "summary": summary},
                       "allowed_tools": (["get_incident_record", "get_application_logs"]
                                         if behavior == "permission" else
                                         ["get_incident_record", "get_server_metrics",
                                          "get_application_logs"]),
                       "events": events})
        truth.append({"scenario_id": scenario_id, "root_cause": cause,
                      "expected_findings": [cause],
                      "expected_tools": ["get_incident_record", "get_server_metrics",
                                         "get_application_logs"],
                      "evaluation_minute": 15 if behavior == "recovery" else 10,
                      "expected_behavior": behavior})
    return public, truth


def write_fixtures(public_path: Path = PUBLIC, truth_path: Path = TRUTH) -> None:
    observations, labels = build_records()
    for path, records in ((public_path, observations), (truth_path, labels)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record, sort_keys=True) + "\n"
                                for record in records), encoding="utf-8")


if __name__ == "__main__":
    write_fixtures()
