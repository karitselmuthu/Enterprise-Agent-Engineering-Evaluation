# Verification snapshot — 2026-10-14

This is an interim evidence record. The proposed API endpoints are absent, so
the project is not yet declared complete.

| Item | Observed result |
| --- | --- |
| Local runtime | Python 3.14.7; `mcp` 2.3.0; `pydantic` 2.14.1 |
| Project constraints | Python >=3.11; `mcp>=2.3,<3` |
| CI runtime | Python 3.12 per workflow configuration |
| Local test suite | 76 discovered; 75 passed; 1 Docker integration skipped (daemon unavailable) |
| Agent run | `scripts/run_agent.py INC-001` selected `get_incident` with `incident_id=INC-001`, returned `ok=true`, and included cause and recommended action |
| Tool-call benchmark | Three fixture cases; tool selection accuracy 1.0, trajectory accuracy 1.0, execution success 1.0 |
| MCP integration | Discovery and structured call tests pass; missing incident, invalid argument, denied tool, and unknown tool cases pass |
| Retrieval | Five fixed queries ranked their expected runbook first: top-1 accuracy 5/5 on teaching fixtures |
| Evaluation | Three-case mock benchmark passed; mean answer-term recall 1.0. Dataset → injected judge → report integration passed; invalid judge output rejected. Local model judge score: not verified |
| Simulation replay | 20 scenarios, four virtual timestamps each; 60 attempted tool calls, 58 successful; expected tool coverage 1.0; literal root-cause phrase rate 0.0 (not semantic accuracy) |
| Docker smoke test | Local daemon unavailable; CI Docker job passed on verification commit `77e5644`, including generated-code execution |
| API endpoints | Not implemented or verified |

Commands used locally:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python scripts/run_evaluation.py
.venv/bin/python scripts/run_agent.py INC-001
.venv/bin/python -m scripts.run_simulation
```

The simulation milestone's `tests` and `docker-sandbox` jobs both passed in
[GitHub Actions run 38559000896](https://github.com/karitselmuthu/Enterprise-Agent-Engineering-Evaluation/actions/runs/38559000896).

## Hardware and production gaps

- The development Mac has 8 GB unified memory. Mock execution is the default;
  local model judging has not been measured on this machine.
- Docker CLI 29.6.2 is installed, but the daemon was unavailable during local
  verification. The sandbox fails closed without Docker.
- MCP reads local fixtures. There is no deployed server, remote authentication,
  or production infrastructure connector.
- Runbooks and benchmark cases are small teaching fixtures. Their scores do
  not establish production accuracy or resilience to distribution shift.
- The replay scenarios are synthetic and currently share one fixed generation
  seed and four timestamps. No live simulator or holdout scenario set exists.
- No live Ollama or hosted-model quality, latency, cost, or reliability scores
  have been collected.
- The proposed API, metrics export, operational monitoring, and production
  authorization workflow remain unimplemented.
