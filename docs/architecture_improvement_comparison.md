# Architecture review: structure comparison and implementation record

The user-provided *Enterprise Agent Evaluation: Architecture Review and Improvement Areas* PDF is a research review and proposed roadmap, not a repository instruction file. This change implements its highest-priority read-only foundation within the current package layout. Existing modules stay in place so experiment imports, scripts, and tests keep working.

## Folder and file comparison

| Review recommendation | Before this change | After this change | Decision |
| --- | --- | --- | --- |
| Explicit state machine, budgets, and events under `src/enterprise_agent/core/` | `src/agents/state.py` held request, result, trace, and answer; no enforced run lifecycle | `src/agents/investigation.py` adds legal transitions, call and wall-time budgets, sequential events, and create-once JSONL export; `state.py` holds the record | Implemented in the existing `src/agents/` package; no broad namespace move |
| First-class policy package, with risk, scopes, approval, and post-action verification | `src/tools/permissions.py` checked allowed tool names only | `src/policy/engine.py` and metadata in `src/tools/registry.py`; `src/tools/executor.py` enforces policy, exposes preflight and status taxonomy, and verifies approved side effects | Implemented; no operational mutating tools are registered |
| Evidence cards with source, time, and raw observation reference | Replay investigator appended evidence strings directly to the answer | `src/evidence/schema.py`, `store.py`; `src/agents/simulation_agent.py` creates cards from visible tool output and cites cards in findings | Implemented for the deterministic replay investigator; no causal proof or general LLM evidence normalizer yet |
| Process and repeated-run evaluation under `evaluation/` | `src/evaluation/scenario_validation.py` scored one run per scenario using deterministic cues | `src/evaluation/process_validation.py`, `scripts/validate_process.py`, and focused unit/integration tests check state transitions, budget, citation references, and 3/5-trial workflow proxy | Implemented as a process metric; diagnosis quality remains unmeasured |
| First-class observability package with durable traces | Ad hoc `AgentState.trace` list | `InvestigationRecord.events` has investigation ID, sequence, timestamp, phase, event kind, and can export a JSONL artifact | Partial; no automatic durable store, OpenTelemetry export, or retention policy |
| Harden generated-code sandbox | `src/coding_agents/sandbox.py` already sets non-root, no network, read-only filesystem, CPU/memory/PID limits, timeout, output cap, and removes containers | Same path and controls retained | No structural change needed for this milestone; rootless daemon remains an operator setting |
| Retrieval, memory, MCP, API, and provider tiers | Existing `src/retrieval/`, `src/memory/`, `src/mcp/`, optional Ollama, and reserved `api/` | Existing paths retained | Broader provenance lifecycle, retrieval benchmark, remote authenticated MCP, and API are future milestones |

### Files added

```text
src/agents/investigation.py
src/evidence/__init__.py
src/evidence/schema.py
src/evidence/store.py
src/policy/__init__.py
src/policy/engine.py
src/evaluation/process_validation.py
scripts/validate_process.py
tests/unit/test_policy_and_investigation.py
tests/integration/test_evidence_process.py
docs/architecture_improvement_comparison.md
```

### Existing files changed

```text
src/agents/state.py
src/agents/simulation_agent.py
src/tools/registry.py
src/tools/executor.py
README.md
docs/architecture.md
docs/limitations.md
.github/workflows/ci.yml
```

No existing folder was renamed or removed. The review's suggested `src/enterprise_agent/` namespace is a possible future migration, not a requirement for these controls. Moving every package now would add import churn without improving the replay boundary.

## Behavior and limits

`SimulationInvestigator` reads the public replay observations only. It never reads private root-cause labels. Its evidence cards point to run-local tool results and the answer cites the cards it uses. The card confidence is a deterministic extraction confidence, not a diagnosis probability. A tool denial or call-budget exhaustion remains visible in the run record and answer.

The policy engine is host code. A name allowlist alone cannot enable a side-effecting tool: the caller must also grant mutation, matching scopes, and approval where required. Side-effecting registrations must provide a verifier; an accepted handler response alone is not considered verified state change. The project still has no human approval workflow or registered mutating production tool.

The repeatability report checks process invariants and required tool names. `pass_at_1_proxy_rate` and `all_success_proxy_rate` do **not** measure semantic root-cause accuracy, evidence closure, or safe remediation. The existing 25 replay cases remain a small deterministic teaching set; repeated identical mock runs do not estimate model variance.

## Run the new checks

```bash
python3 -m unittest tests.unit.test_policy_and_investigation tests.integration.test_evidence_process -v
python3 -m scripts.validate_process --trials 3 --output /tmp/process-3.json
python3 -m scripts.validate_process --trials 5 --output /tmp/process-5.json
```

The script exits nonzero if any scenario fails its workflow proxy. Review `results[].attempts` for the failed condition. Existing scenario and reliability scripts remain the outcome and fault probes described in the README.

On 2026-10-17, the repository test suite passed 130 tests with 2 optional Docker tests skipped after the payment-latency extension. The 25 replay scenarios passed the five-trial workflow proxy, and the existing local reliability workload passed its seven checks. These results use the deterministic mock backend.

## Subsequent payment-latency scenario extension

The `SIM-004` workflow now has a sixth read-only tool, `get_database_metrics`.
`simulation/event_generator.py` and the two JSONL datasets add public pool
observations and a private expected-tool entry. `simulation/engine.py`,
`simulation/scenario_loader.py`, and `simulation/adapters/metrics_api.py` expose
and validate time-bounded database samples. `simulation/faults.py` creates
missing-sample, timeout, and misleading-log variants without private labels.
`src/agents/simulation_agent.py` records a typed hypothesis and cites latency
and pool evidence; `src/evaluation/database_latency_eval.py` scores each
variant. `scripts/validate_database_latency.py`,
`tests/scenarios/test_database_latency.py`, and the
[dated result](../reports/database_latency_scenario_2026-10-17.md) make the
extension runnable and reviewable. Existing package paths remain in place.

## Recommended later work

1. Add typed response schemas and bounded retry policy to all native and MCP tools, including contract versioning.
2. Add automated durable event storage and OpenTelemetry-compatible spans with redaction and retention.
3. Define claim-level evidence closure and labelled causal-path scenarios before reporting groundedness or RCA accuracy.
4. Build a labelled runbook retrieval benchmark; add embedding or hybrid retrieval only if it improves measured results.
5. Add memory provenance, approval, review, expiry, and contradiction tests.
6. Benchmark prompt injection in logs and runbooks, and extend host policy to remote MCP calls with authenticated transport.
7. Add a human approval workflow and independent state verification before registering operational write tools.
