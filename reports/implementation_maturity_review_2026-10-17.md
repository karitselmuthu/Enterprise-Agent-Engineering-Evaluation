# Code-level implementation maturity review — 2026-10-17

## Scope and verdict

This review inspects the current local code and runs the repository's deterministic
replay, reliability, unit, integration, and optional local Ollama paths. It does
not certify production readiness. The primary `SIM-004` replay workflow works,
but the architecture diagram currently combines capabilities that live in
different agent implementations. In particular, the evidence-rich replay agent
does not use Ollama or SQLite memory, and the Ollama agent does not run the
replay investigation.

| Review question | Status | Evidence and limit |
| --- | --- | --- |
| End-to-end database investigation | **Demonstrated in replay** | `scripts.validate_database_latency` passed baseline, missing metrics, timeout, and misleading logs at virtual minute 25; all four workflow scores were 1.00. The result is a deterministic, rule-based investigation, not an LLM root-cause assessment. |
| Tool authorization cannot be bypassed | **Not established as a security boundary** | `ToolExecutor` rejects a mutating tool under default policy. The same registered handler is directly callable through `ToolRegistry.get(...).handler`, bypassing the executor. `MCPIncidentAgent` has its own allowlist and does not use `PolicyContext`. Host code and plugin registration must therefore be trusted. |
| Evidence persisted and traceable | **Traceable in memory; incomplete persistence** | The baseline run had six evidence cards, four tool results, and valid in-memory citation references. An explicit `InvestigationRecord.write_jsonl` export wrote 36 events, but neither raw observations nor evidence cards. Replay runs do not automatically write this artifact or use the separate SQLite memory agent. Citations cannot be reconstructed from the export alone. |
| Evaluation scores reproducible | **Demonstrated for deterministic proxies** | Two independent database report files had identical SHA-256 `cf8a1fcae3033a51d27099c0de5bd376dbc20b004ee342395c348883126f40d7`. Two 25-scenario × 5-trial process reports were also byte identical (`c83a1088c4eef31a92cb44a27b4b85e50eaf758232e2cb40dd4cc588f93696c4`). Scores check workflow, tool names, and citation references; they do not validate semantic diagnosis or remediation quality. |
| Failure handling | **Demonstrated for controlled faults; material timeout risk** | Four `SIM-004` variants passed. The synthetic reliability workload passed 10 concurrent and 50 sequential investigations, malformed output, temporary MCP outage/recovery, repeated requests, and bounded investigation timeout. A timed-out synthetic mutating handler still completed after `ToolExecutor` returned `TIMEOUT`; Python worker threads are not forcibly stopped. |
| Ollama on this 8 GB Mac | **Basic tool use works with variable latency** | On MacBook Neo (Apple A18 Pro, 8 GB), installed `chat-lowram:latest` selected `get_incident` and completed in 14.46 s; `llama3.2:3b` did so in 7.91 s, then 8.09 s and 21.30 s on two further requests. The installed `qwen2.5-coder:1.5b` returned no tool choice in 2.95 s and 0.58 s. This tests the simple `IncidentAgent` with one fixture tool call, not the replay investigator, multi-step reasoning, sustained load, or memory pressure. |

## Reproduction

Run from the repository root in the existing environment:

```bash
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -q
.venv/bin/python -m scripts.validate_database_latency --output /tmp/eae-db-review.json
.venv/bin/python -m scripts.validate_process --trials 5 --output /tmp/eae-process-review.json
.venv/bin/python -m scripts.validate_reliability --output /tmp/eae-reliability-review.json
```

The full suite ran **130 tests, OK, two skipped**. The two skipped tests require
the opt-in Docker integration environment. The first sandboxed full-suite run
failed only because the local HTTP integration test could not bind loopback;
rerunning with local loopback permission passed. Python was 3.14.7. The
reliability report was passing, with median synthetic investigation time
0.451 ms and p95 12.815 ms; these are in-process fixture timings and exclude
Ollama.

## Code-path findings

1. **Authorization applies at the executor boundary.** `src/tools/executor.py`
   calls `preflight`, and `src/policy/engine.py` rejects mutations by default,
   checks scopes, and requires a verifier. `src/tools/registry.py` returns the
   `Tool` object including its handler. A synthetic in-memory probe observed
   `policy_denied` and zero handler calls through the executor, then one call
   through `registry.get("change").handler()`. This is a proof of an in-process
   bypass by trusted Python code, not a claim that model text alone can bypass
   the executor. Caller-supplied `PolicyContext.approved_tools` is not an
   authenticated approval record.
2. **Timeout is observational, not cancellation.** The executor uses
   `future.result(timeout=...)` and `future.cancel()`. A synthetic side-effect
   handler sleeping 60 ms returned `timeout` at 5 ms, then made its in-memory
   change after the result was returned. Read-only replay tools avoid the
   immediate infrastructure risk; any future mutating integration needs a
   cancellable process/service boundary, idempotency, and explicit reconciliation.
3. **Evidence references depend on the live state.** `EvidenceStore` is a list
   of cards with run-local `ev-####` IDs. A card's `tool-result://run/index`
   reference resolves only while `AgentState.tool_results` remains available.
   `InvestigationRecord.write_jsonl` saves events on explicit request and has
   no corresponding replay-state loader. The SQLite memory classes serve the
   separate stateful incident agent. A durable investigation artifact should
   store versioned cards, tool result snapshots, citations, and run metadata
   together, then verify them after reload.
4. **The process score is a proxy.** `inspect_process` checks phase order,
   budget, tool-result references, and citation membership. The database
   evaluator uses ten Boolean checks per variant. The private scenario label
   is used by the evaluator, while the agent receives public observations.
   These checks give strong regression coverage for the coded flow, but a
   valid-looking wrong diagnosis could still satisfy general process checks.
5. **Fault coverage is useful but narrow.** The reliability module injects
   one MCP connection outage and recovery, one malformed response, synthetic
   latency, and bounded process timeout. It does not establish repeated MCP
   retry policy, distributed concurrency safety, crash recovery, or sustained
   service load. `SimulationInvestigator._call` also records `policy_checked`
   as allowed when given a custom tool object without `preflight`; the normal
   `ToolExecutor` path does have `preflight`, but injected adapters can produce
   a misleading audit event.
6. **Ollama is an alternate, simpler path.** `src/llm/local_backend.py` sends
   a tool-choice request and an interpretation request to `/api/chat` with a
   30-second HTTP timeout. `IncidentAgent` uses the old two-tool fixture
   registry and makes one tool call. Its incident fixture already contains a
   `suspected_cause`, so a fluent answer does not demonstrate independent
   root-cause identification. `ollama ps` showed `llama3.2:3b` occupying 2.5 GB
   on the GPU with 4096 context; overall system memory pressure was not
   measured. Local results are model and prompt specific, and the 21.30 s
   request shows meaningful latency variation even in this small sample.

## Priority before claiming architecture maturity

1. Persist complete replay investigations and prove citation resolution after
   restarting the process.
2. Define one trusted execution boundary for all agent paths, including MCP;
   keep untrusted code away from raw tool handlers and derive approval state
   from an authenticated host context.
3. Keep mutating tools out of thread-timeout execution. Add an isolated,
   cancellable execution boundary and test what happens when completion arrives
   after a timeout.
4. Add outcome checks for diagnosis quality and false positives alongside
   deterministic workflow scores.
5. Integrate a local model with the evidence-rich replay investigation before
   using Ollama timings as evidence of multi-step agent performance; measure
   repeated-run latency and memory pressure under that workload.
