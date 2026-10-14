# Verification snapshot — 2026-10-14

This is an interim evidence record. The proposed API endpoints are absent, so
the project is not yet declared complete.

| Item | Observed result |
| --- | --- |
| Local runtime | Python 3.14.7; `mcp` 2.3.0; `pydantic` 2.14.1 |
| Project constraints | Python >=3.11; `mcp>=2.3,<3` |
| CI runtime | Python 3.12 per workflow configuration |
| Local test suite | 86 discovered; 85 passed; 1 Docker integration skipped (daemon unavailable) |
| Agent run | `scripts/run_agent.py INC-001` selected `get_incident` with `incident_id=INC-001`, returned `ok=true`, and included cause and recommended action |
| Tool-call benchmark | Three fixture cases; tool selection accuracy 1.0, trajectory accuracy 1.0, execution success 1.0 |
| MCP integration | Discovery and structured call tests pass; missing incident, invalid argument, denied tool, and unknown tool cases pass |
| Retrieval | Five fixed queries ranked their expected runbook first: top-1 accuracy 5/5 on teaching fixtures |
| Evaluation | Three-case mock benchmark passed; mean answer-term recall 1.0. Dataset → injected judge → report integration passed; invalid judge output rejected. Local model judge score: not verified |
| Simulation replay | 20 scenarios; 19 have four timestamps and payment has eight; 60 attempted tool calls, 58 successful; expected tool coverage 1.0; literal root-cause phrase rate 0.0 (not semantic accuracy) |
| Mode A acceptance | Payment incident observations and advice differ at 10:15 and 10:25 UTC; recovery observed at 10:35 UTC; all replay checks pass |
| Mode B acceptance | Eight payment events published over 0.354 wall seconds; three polling clients made 96 polls, with three investigations in flight; pacing, snapshot, ordering, and final recovery checks pass |
| Five-category data volume audit | 0 standalone inventory records, 80 metric samples, 82 log entries, 20 simulated alerts plus 1 separate fixture incident, 5 runbooks; none meets the suggested initial volume |
| Docker smoke test | Local daemon unavailable; CI Docker job passed on Mode A commit `dd0c9ff`, including generated-code execution |
| API endpoints | Not implemented or verified |

Commands used locally:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python scripts/run_evaluation.py
.venv/bin/python scripts/run_agent.py INC-001
.venv/bin/python -m scripts.run_simulation
.venv/bin/python -m scripts.audit_data
.venv/bin/python -m scripts.validate_mode_a
.venv/bin/python -m scripts.validate_mode_b
```

The Mode A commit's `tests` and `docker-sandbox` jobs both passed in
[GitHub Actions run 38561760377](https://github.com/karitselmuthu/Enterprise-Agent-Engineering-Evaluation/actions/runs/38561760377).

## Hardware and production gaps

- The development Mac has 8 GB unified memory. Mock execution is the default;
  local model judging has not been measured on this machine.
- Docker CLI 29.6.2 is installed, but the daemon was unavailable during local
  verification. The sandbox fails closed without Docker.
- MCP reads local fixtures. There is no deployed server, remote authentication,
  or production infrastructure connector.
- Runbooks and benchmark cases are small teaching fixtures. Their scores do
  not establish production accuracy or resilience to distribution shift.
- The scenarios are synthetic and deterministic. Nineteen have four timestamps
  and the payment case has eight. Mode B paces existing events; it does not
  synthesize novel events while running or include a holdout scenario set.
- No live Ollama or hosted-model quality, latency, cost, or reliability scores
  have been collected.
- The proposed API, metrics export, operational monitoring, and production
  authorization workflow remain unimplemented.
