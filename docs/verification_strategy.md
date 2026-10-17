# Verification strategy

## Test policy

Every new phase must include deterministic fixtures, focused unit tests,
integration tests across the relevant component boundary, negative cases, and
failure-handling assertions. A test that only repeats implementation logic is
insufficient. Keep the mock backend as the default; live Ollama and hosted
providers are optional experiments and must be reported separately.

Run the baseline checks from the repository root:

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
python3 scripts/run_evaluation.py
python3 -m scripts.run_simulation
python3 -m scripts.audit_data
python3 -m scripts.validate_mode_a
python3 -m scripts.validate_mode_b
python3 -m scripts.validate_scenarios
python3 -m scripts.validate_reliability
python3 -m scripts.report_operational_metrics
python3 -m scripts.generate_synthetic
python3 -m scripts.validate_synthetic_load
```

CI runs these commands on Python 3.12 and runs the Docker sandbox integration
test in a separate job. The local Docker test is opt in with
`RUN_DOCKER_INTEGRATION=1` and requires a running daemon and the
`python:3.12-alpine` image.

| Area | Unit and negative checks | Integration and failure checks |
| --- | --- | --- |
| Tool calling | Selection, schema, unknown tool, permissions, timeout, execution error | Fixture-backed agent result and trace |
| MCP | Tool conversion and permission handling | Discovery, structured invocation, invalid input, missing incident, denied tool |
| Memory and retrieval | Session and index behavior | Resume across instances, MCP investigation, cited runbook guidance |
| Context and coding | Budget, static validation, sandbox command | Long session resume, Docker generated-code smoke test |
| Skills | Manifest validation and policy | MCP skill invocation and tool errors |
| Evaluation | Metrics, dataset validation, judge response validation, bias probes, benchmark gate | Dataset → injected judge → report, plus MCP and retrieval agent states scored through the evaluator, including invalid judge output and failed incident lookup |
| Simulation | Virtual clock, public loader, fixture regeneration, future-event hiding, unknown resource | Twenty-five scenario runs through the standard tool executor, missing data, timeout, denied tool, and label separation |
| Declarative synthetic simulation | Five blueprint generation, invalid metrics, private-label rejection | Agent → standard tool executor → frozen replay snapshot; 10 concurrent and 50 sequential local reads |
| Optional data and live setup | JSONL log mapping, invalid timestamps and severities, local URL restriction | Loopback HTTP fault and recovery through standard tools; opt-in Compose smoke test |

## Scenario evaluation

`python3 -m scripts.validate_scenarios` investigates all 25 cases at their
evaluation minutes. The scorer accepts any order of required tool calls and
additional permitted calls. It checks that a case-specific source marker is
present in successful tool output; missing telemetry, expected timeout, and
expected permission denial have explicit handling. Tool and evidence checks
form the deterministic CI gate. The report also records an exact cause phrase
proxy and case-specific recommendation cues. Those narrow text checks can
reject valid paraphrases or accept quoted logs without true causal reasoning;
review failing cases or use a calibrated judge before calling them semantic
accuracy. The agent never receives the private rubric.

## Initial reliability workload

`python3 -m scripts.validate_reliability` runs 10 synchronized concurrent
investigations, 50 sequential requests, and five repeats of the same request.
It also checks a delayed tool timeout, temporary MCP connection loss followed
by recovery, malformed tool content, and a stalled investigation terminated
at a process boundary. `--concurrent` and `--sequential` change the counts.
The report includes pass/fail checks and observed timings. This workload uses
synthetic local tools and is not an enterprise throughput or latency benchmark.

## Operational metric contract

`python3 -m scripts.report_operational_metrics` combines the scenario and
reliability JSON reports. Tool selection is the share of scenarios selecting
all required tool names, with call order unconstrained. Tool execution success
counts successful tool responses over attempted invocations, including the
two expected failure cases. Average tool calls is attempts per scenario.
End-to-end latency covers scenario dispatch through answer on the local mock
backend and reports mean, median, and nearest-rank p95. Recovery success is
successful recovery after an injected temporary MCP outage; currently its
denominator is one.

Task completion, root-cause identification accuracy, evidence groundedness,
hallucination rate, and token consumption are `not_measured` in this baseline.
The report retains exact cause wording, source evidence availability, and a
strict deterministic completion cue as diagnostics only. Valid semantic scores
need adjudicated case outcomes and claim-level evidence labels; token use needs
backend usage telemetry. Do not treat a `null` value as zero or a cue as an
accuracy score.

## Proposed API verification contract

The following routes are **not implemented**. When an API layer is added,
verify its request and response schema, status codes, validation failures,
authorization behavior, and idempotency or persistence where relevant. Use a
test client with deterministic fixtures in CI; reserve network smoke tests for
deployment environments.

| Route | Success check | Negative and failure check |
| --- | --- | --- |
| `GET /health` | Service responds with a machine-readable status | Dependency failure is represented clearly |
| `POST /v1/agents/run` | Valid request returns a run identifier and result or accepted status | Invalid input, denied tool, and tool failure are distinguishable |
| `GET /v1/agents/{run_id}` | Existing run returns stored status, trace, and result | Unknown ID returns a documented not-found response |
| `POST /v1/evaluations/run` | Valid dataset runs evaluation and returns report identity or result | Invalid dataset and judge failure are reported without a false score |
| `GET /metrics` | Exposes documented counters and timings | Sensitive request content and secrets are absent |

## Final evidence record

Before declaring the project complete, create or update a dated verification
report under `reports/`. Record exact Python and dependency versions, test
counts and skips, commands and fixture IDs, tool-call and MCP results,
retrieval ranking, deterministic and model-based evaluation scores, Docker
smoke-test environment, hardware limits, and production gaps. Label anything
not run as **not verified**. The current snapshot is
[`reports/verification_2026-10-17.md`](../reports/verification_2026-10-17.md).
