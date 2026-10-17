# Payment latency and database pool investigation

Run `python3 -m scripts.validate_database_latency` from the repository root.
It writes the complete per-check JSON report to
`reports/scenario_results/database_latency.json`. The test source is
`tests/scenarios/test_database_latency.py`.

The operator starts `SIM-004` at virtual 10:25 UTC. The read-only agent obtains
the incident, server metrics, database metrics, and logs through the normal
tool executor. At 10:25, request latency is 810 ms; database pool occupancy is
40/40 with 65 requests waiting. The agent records source-linked evidence
cards, proposes pool exhaustion as a *likely contributing cause*, checks the
metric support, and cites the latency and database cards in its conclusion.
The latency rise started before complete pool saturation, so the answer asks
for dependency timing confirmation before any change.

| Variant | Database tool | Finding | Key behavior | Evaluation |
| --- | --- | --- | --- | --- |
| Baseline | Success | Supported hypothesis | Cites elevated latency and saturated pool; recommends investigation and escalation | Pass |
| Missing database metrics | Success, empty samples | Insufficient evidence | Does not adopt the pool-exhaustion log as proof | Pass |
| Database tool timeout | Timeout | Insufficient evidence | Reports unavailable telemetry and avoids a root-cause claim | Pass |
| Misleading logs | Success | Supported hypothesis with conflict | Flags the “pool healthy” log against measured 40/40 occupancy | Pass |

The evaluator checks investigation start, source tool selection, latency
detection before the database call, authorization, tool outcome, evidence-card
presence, hypothesis verification, citations, and lifecycle events. All four
variants scored 1.00 locally on 2026-10-17. A failed authorization check
fails the variant even if its other checks pass. This is a deterministic simulated
workflow score; it is not proof of causality, semantic RCA accuracy, or
production readiness. No model is invoked in this experiment.
