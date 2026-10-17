# Incident scenario catalog

The corpus contains 25 distinct synthetic investigations. Each public scenario
has a linked incident, service, server, UTC event timeline, tool permissions,
metrics, and logs. Specialized cases also have pod events, peer network
samples, or a related incident. Evaluation expectations live in
`data/evaluation_datasets/simulation_ground_truth.jsonl`; runtime tools load
only `data/simulation/scenarios.jsonl`.

| ID | Scenario | Evidence the agent should use |
| --- | --- | --- |
| SIM-001 | CPU saturation | Sustained high CPU and delayed requests |
| SIM-002 | Memory leak | Rising memory and an out-of-memory restart |
| SIM-003 | Disk exhaustion | Near-full disk and write failure |
| SIM-004 | Database connection pool exhaustion | Request latency, database pool utilization and waiters, application logs, recovery |
| SIM-005 | Database unavailable | Database health warning and refused connections |
| SIM-006 | Kubernetes pod crash loop | Pod restart events and container-exit logs |
| SIM-007 | Network latency | One slow peer path and one healthy peer path |
| SIM-008 | Deployment regression | Release event followed by application errors |
| SIM-009 | Authentication failures | Rising failed logins and rejected users |
| SIM-010 | Concurrent CPU and database incidents | Separate payment and billing incident IDs and logs |
| SIM-011 | Missing telemetry | No metric samples or diagnostic logs |
| SIM-012 | Metrics tool timeout | Failed metrics call with remaining log evidence |
| SIM-013 | Conflicting monitoring evidence | Normal CPU metrics and contradictory application log |
| SIM-014 | Recovery after CPU saturation | CPU peak followed by resolved status and lower CPU |
| SIM-015 | Repeated alerts | Repeated latency alert without a new failure mode |
| SIM-016 | Permission denied on metrics | Denied metrics request while logs stay available |
| SIM-017 | Healthy infrastructure | Healthy status and no errors |
| SIM-018 | Cache outage | Falling hit ratio, cache failure, rising database load |
| SIM-019 | Message queue backlog | Increasing queue depth and consumer lag |
| SIM-020 | Expired TLS certificate | Expiry warning and rejected TLS handshakes |
| SIM-021 | DNS resolution failure | DNS retries and NXDOMAIN error |
| SIM-022 | Database replication lag | Rising replica lag and stale reads |
| SIM-023 | Storage I/O latency | High write latency with available disk capacity |
| SIM-024 | API rate limiting | Quota warning and HTTP 429 responses |
| SIM-025 | Regional network degradation | Two slow regional peers and a healthy local peer |

Each private record defines `scenario_id`, `scenario_name`, `affected_service`,
at least two `expected_findings`, `expected_tools`, `expected_behavior`, and an
`evaluation_minute`. For example, `SIM-004` is evaluated at minute 25, after
the pool exhaustion and request failures become visible. The private rubric
describes desired behavior; it is not injected into the agent. Cases without a
confirmed operational cause, including healthy infrastructure and missing
telemetry, have a null `root_cause` and are excluded from the literal phrase
rate.

The payment case's private rubric includes:

```json
{
  "scenario_id": "SIM-004",
  "scenario_name": "Database connection pool exhaustion",
  "affected_service": "payment-service",
  "expected_findings": [
    "Database pool exhausted",
    "Request latency and failures increase"
  ],
  "expected_tools": [
    "get_incident_record",
    "get_server_metrics",
    "get_application_logs",
    "get_database_metrics"
  ],
  "expected_behavior": "Identify database connection exhaustion as a likely cause and recommend further investigation.",
  "evaluation_minute": 25
}
```

Regenerate the deterministic files and inspect the evaluation report:

```sh
python3 -m simulation.event_generator
python3 -m scripts.run_simulation
python3 -m scripts.validate_scenarios
python3 -m scripts.validate_database_latency
python3 -m unittest tests.integration.test_scenario_catalog -v
```

The report is written to `reports/scenario_results/replay.json`. It shows each
rubric beside the selected tools and answer. The current baseline investigates
observations and demonstrates tool access, but its literal root-cause metric is
not a semantic judgment of the expected behavior. `SIM-010` contains two
distinct alerts, so the 25 scenario cases represent 26 simulated alert records.
The separate `scenario_validation.json` report checks all 25 complete
investigations with order-independent tool selection and visible-source
evidence. It records conservative cause and recommendation cues separately.
`validate_database_latency` also runs the same payment investigation with
missing database samples, an injected database-tool timeout, and contradictory
application logs. Its deterministic evaluator checks tool authorization,
time ordering, evidence references, hypothesis status, and safe uncertainty.
