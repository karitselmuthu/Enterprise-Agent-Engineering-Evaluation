"""Offline fixture generator. Runtime replay never imports this module."""

import json
from datetime import datetime, timedelta, timezone
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
    ("SIM-010", "Two alerts on one host", "Concurrent CPU and database incidents", "Payment worker CPU high", "Payment worker CPU queue saturated", "cpu", "degraded"),
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
    ("SIM-021", "Service cannot resolve dependency", "DNS resolution failure", "DNS lookup retries increasing", "Dependency hostname lookup failed: NXDOMAIN", "network", "degraded"),
    ("SIM-022", "Reads return stale data", "Database replication lag", "Replica delay increasing", "Read replica is 180 seconds behind primary", "normal", "degraded"),
    ("SIM-023", "Writes slow despite free capacity", "Storage I/O latency", "Storage write latency increasing", "Disk I/O wait exceeded threshold", "normal", "degraded"),
    ("SIM-024", "Clients receive HTTP 429", "API rate limiting", "Request quota nearing limit", "Rate limit exceeded; requests rejected with HTTP 429", "normal", "degraded"),
    ("SIM-025", "Several regional services slow", "Regional network degradation", "Cross-region path latency increasing", "Regional network path timed out for two services", "network", "degraded"),
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
    "shipping-api", "reporting-api", "storage-gateway", "public-api", "regional-gateway",
)

# Evaluation-only expectations. These are written to the private label file.
EXPECTATIONS = {
    "SIM-001": (["CPU remains above 90%", "Requests delayed"], "Identify sustained CPU saturation and inspect worker capacity."),
    "SIM-002": (["Memory rises across samples", "Out-of-memory restart"], "Recognize a growing memory trend and investigate allocation or leak sources."),
    "SIM-003": (["Disk usage approaches capacity", "No space left on device"], "Identify low remaining disk capacity and investigate disk consumers."),
    "SIM-004": (["Database pool exhausted", "Request latency and failures increase"], "Identify database connection exhaustion as a likely cause and recommend further investigation."),
    "SIM-005": (["Database connection refused", "Database requests fail"], "Correlate application errors with database availability."),
    "SIM-006": (["Pod restart count increases", "Container exits repeatedly"], "Inspect pod events and application logs before diagnosing the crash loop."),
    "SIM-007": (["One peer path has high latency", "Other peer path remains near baseline"], "Compare network metrics across services and isolate the affected path."),
    "SIM-008": (["Release occurs before errors", "Errors increase after release"], "Correlate the regression with the recent deployment and verify rollback options."),
    "SIM-009": (["Failed logins increase", "Authentication rejections affect many users"], "Identify abnormal authentication failures without assuming an attack."),
    "SIM-010": (["CPU saturation affects payment gateway", "Database connection failures affect billing API"], "Distinguish the two incident IDs and investigate their evidence separately."),
    "SIM-011": (["Metric samples are absent", "Diagnostic logs are absent"], "Report insufficient evidence and request monitoring restoration."),
    "SIM-012": (["Metrics tool times out", "Application logs remain available"], "Retry within configured limits or fail gracefully without inventing metrics."),
    "SIM-013": (["Metrics show normal CPU", "Application log reports CPU saturation"], "Explain the conflicting evidence and request another measurement."),
    "SIM-014": (["CPU falls after peak", "Service status resolves"], "Recognize recovery and recommend sustained monitoring."),
    "SIM-015": (["Alert repeats", "No separate failure mode appears"], "Treat repeated alerts as one incident unless new evidence appears."),
    "SIM-016": (["Metrics access is denied", "Logs remain available"], "Respect the permission boundary and report limited visibility."),
    "SIM-017": (["Service stays healthy", "No errors observed"], "Avoid inventing an active incident."),
    "SIM-018": (["Cache backend unavailable", "Database load rises"], "Investigate the cache dependency before attributing database load to the database itself."),
    "SIM-019": (["Queue depth increases", "Consumer lag exceeds threshold"], "Investigate consumer capacity and queue backlog."),
    "SIM-020": (["Certificate expires", "TLS handshakes fail"], "Check certificate validity and affected endpoints."),
    "SIM-021": (["DNS lookup fails", "Dependency requests cannot resolve hostname"], "Investigate DNS records and resolver availability."),
    "SIM-022": (["Replica lag grows", "Reads return stale data"], "Compare replica lag with primary health before recommending database changes."),
    "SIM-023": (["I/O latency rises", "Disk capacity remains available"], "Distinguish storage I/O latency from disk exhaustion."),
    "SIM-024": (["Quota threshold is reached", "HTTP 429 responses increase"], "Identify rate limiting and inspect client request rate and quota policy."),
    "SIM-025": (["Two regional paths degrade", "Local peer path stays healthy"], "Compare peer network metrics and identify regional scope."),
}
NO_CONFIRMED_CAUSE = {"SIM-011", "SIM-012", "SIM-013", "SIM-015", "SIM-016", "SIM-017"}

REPLAY_START = datetime(2026, 10, 14, 10, 0, tzinfo=timezone.utc)

# The detailed payment timeline is a fixed validation case for evidence changes.
PAYMENT_TIMELINE = (
    (0, 35, 48, "Normal service operation", "INFO", "healthy"),
    (5, 42, 52, "Normal service operation", "INFO", "healthy"),
    (10, 65, 61, "Request latency increasing", "WARN", "degraded"),
    (15, 82, 73, "Database connection warnings near pool limit", "WARN", "degraded"),
    (20, 94, 85, "Database connection pool exhausted", "ERROR", "degraded"),
    (25, 97, 89, "Requests failing after database pool exhaustion", "ERROR", "degraded"),
    (30, 76, 82, "Recovery begins; request failures decreasing", "INFO", "recovering"),
    (35, 43, 59, "Service recovered; request latency normal", "INFO", "resolved"),
)


def _timestamp(minute: int) -> str:
    return (REPLAY_START + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z")


def _payment_events() -> list[dict]:
    events = []
    for minute, cpu, memory, message, severity, status in PAYMENT_TIMELINE:
        timestamp = _timestamp(minute)
        events.append({"minute": minute, "timestamp": timestamp,
                       "metrics": {"cpu_percent": cpu, "memory_percent": memory,
                                   "disk_percent": 45, "network_latency_ms": 20 + max(0, cpu - 35) * 3,
                                   "timestamp": timestamp},
                       "logs": [{"timestamp": timestamp, "severity": severity,
                                 "message": message}],
                       "status": status, "faults": []})
    return events


def build_records() -> tuple[list[dict], list[dict]]:
    public, truth = [], []
    for index, (scenario_id, summary, cause, warning, error, profile, behavior) in enumerate(SPECS, 1):
        service = SERVICES[index - 1]
        server_id = f"prod-app-{index:03d}"
        events = []
        for offset, minute in enumerate((0, 5, 10, 15)):
            timestamp = _timestamp(minute)
            reading = PROFILES[profile][offset]
            metrics = (None if reading is None else dict(zip(
                ("cpu_percent", "memory_percent", "disk_percent", "network_latency_ms"),
                reading)))
            if metrics is not None:
                metrics["timestamp"] = timestamp
                if scenario_id == "SIM-022":
                    metrics["replication_lag_seconds"] = (0, 45, 180, 240)[offset]
                if scenario_id == "SIM-023":
                    metrics["disk_io_latency_ms"] = (4, 40, 190, 230)[offset]
            if offset == 0:
                message, severity = "Routine baseline observation", "INFO"
            elif offset == 1:
                message, severity = warning, "WARN"
            elif offset == 2:
                message, severity = error, "INFO" if behavior == "healthy" else "ERROR"
            else:
                message, severity = ("Service recovered" if behavior == "recovery" else error), (
                    "INFO" if behavior in {"recovery", "healthy"} else "ERROR")
            logs = [{"timestamp": timestamp, "severity": severity, "message": message}]
            if behavior == "repeat" and minute >= 10:
                logs.append({"timestamp": timestamp, "severity": "WARN", "message": warning})
            if behavior == "missing":
                logs = []
            if scenario_id == "SIM-010" and offset >= 1:
                logs.append({"timestamp": timestamp,
                             "service": "billing-api",
                             "severity": "WARN" if offset == 1 else "ERROR",
                             "message": "Database retries rising" if offset == 1
                             else "Billing database connection refused"})
            status = ("healthy" if behavior == "healthy" else
                      "resolved" if behavior == "recovery" and minute == 15 else
                      "open" if minute == 0 else "degraded")
            events.append({"minute": minute, "timestamp": timestamp,
                           "metrics": metrics, "logs": logs,
                           "status": status,
                           "faults": ["get_server_metrics"] if behavior == "timeout" and minute == 10 else []})
            if scenario_id == "SIM-006" and offset >= 1:
                events[-1]["pod_events"] = [{"timestamp": timestamp,
                    "pod": "inventory-worker-0", "reason": "BackOff" if offset >= 2 else "Restarting",
                    "message": "Container restart count increasing" if offset == 1
                    else "Container exited repeatedly after startup"}]
            if scenario_id in {"SIM-007", "SIM-025"}:
                peers = (["inventory-api", "catalog-api"] if scenario_id == "SIM-007"
                         else ["us-east-api", "eu-west-api", "local-api"])
                events[-1]["network_peers"] = [
                    {"timestamp": timestamp, "service": peer,
                     "latency_ms": (20 if offset == 0 or peer in {"catalog-api", "local-api"}
                                    else (80, 220, 300)[offset - 1])}
                    for peer in peers]
        if scenario_id == "SIM-004":
            events = _payment_events()
        incident = {"id": scenario_id, "server_id": server_id,
                    "service": service, "summary": summary,
                    "severity": "P3" if behavior == "healthy" else "P2",
                    "alert_at_minute": 10 if scenario_id == "SIM-004" else 0}
        if scenario_id == "SIM-006":
            incident["pod_name"] = "inventory-worker-0"
        if scenario_id in {"SIM-007", "SIM-025"}:
            incident["network_scope"] = True
        if scenario_id == "SIM-010":
            incident["related_incidents"] = [{"id": "SIM-010-B", "service": "billing-api",
                                              "server_id": server_id,
                                              "summary": "Billing database connection failures"}]
        allowed = ["get_incident_record", "get_application_logs"]
        if behavior != "permission":
            allowed.append("get_server_metrics")
        if scenario_id == "SIM-006":
            allowed.append("get_pod_events")
        if scenario_id in {"SIM-007", "SIM-025"}:
            allowed.append("get_service_network_metrics")
        public.append({"scenario_id": scenario_id,
                       "incident": incident,
                       "allowed_tools": allowed,
                       "events": events})
        findings, expected_behavior = EXPECTATIONS[scenario_id]
        truth.append({"scenario_id": scenario_id, "scenario_name": cause,
                      "affected_service": service,
                      "root_cause": None if scenario_id in NO_CONFIRMED_CAUSE else cause,
                      "expected_findings": findings,
                      "expected_tools": ["get_incident_record", "get_server_metrics",
                                         "get_application_logs"]
                                        + (["get_pod_events"] if scenario_id == "SIM-006" else [])
                                        + (["get_service_network_metrics"]
                                           if scenario_id in {"SIM-007", "SIM-025"} else []),
                      "evaluation_minute": (25 if scenario_id == "SIM-004" else 15
                                            if scenario_id in {"SIM-001", "SIM-014"} else 10),
                      "expected_behavior": expected_behavior})
    return public, truth


def write_fixtures(public_path: Path = PUBLIC, truth_path: Path = TRUTH) -> None:
    observations, labels = build_records()
    for path, records in ((public_path, observations), (truth_path, labels)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(record, sort_keys=True) + "\n"
                                for record in records), encoding="utf-8")


if __name__ == "__main__":
    write_fixtures()
