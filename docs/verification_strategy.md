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
```

CI runs both commands on Python 3.12 and runs the Docker sandbox integration
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
[`reports/verification_2026-10-14.md`](../reports/verification_2026-10-14.md).
