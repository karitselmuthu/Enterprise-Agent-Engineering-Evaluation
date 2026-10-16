# Operational metric verification — 2026-10-17

This snapshot covers the local deterministic simulation agent and its 25
synthetic scenarios. It does not establish production accuracy or capacity.

| Check | Local result |
| --- | --- |
| Runtime | Python 3.14.7, `mcp` 2.3.0, `pydantic` 2.14.1 |
| Full unit, integration, and evaluation suite | 102 tests discovered; 101 passed; 1 opt-in Docker test skipped locally |
| Scenario and reliability commands | Both passed; 25 scenarios, 10 concurrent investigations, 50 sequential requests |
| Tool Selection Accuracy | 25/25 = 1.00, required tool names per scenario |
| Tool Execution Success Rate | 78/80 = 0.975, including two expected fault responses |
| Recovery Success Rate | 1/1 = 1.00 after an injected MCP outage; sample too small for a reliability estimate |
| Average Tool Calls | 80/25 = 3.2 attempted calls per investigation |
| End-to-End Latency | Mean, median, and p95 measured locally; rerun for machine-specific values in `operational_metrics.json` |
| Task Completion, Root Cause Accuracy, Evidence Groundedness, Hallucination Rate, Token Consumption | Not measured; report values are `null` with reasons |
| Deterministic diagnostic proxies | Source evidence 25/25; exact cause wording 0/19; strict completion cue 3/25. These are not semantic scores. |

Run from the repository root:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m scripts.validate_scenarios
.venv/bin/python -m scripts.validate_reliability
.venv/bin/python -m scripts.report_operational_metrics
```

The metric report is `reports/scenario_results/operational_metrics.json`.
It records numerator and denominator for fractions, local latency statistics,
and an explicit reason for each unmeasured metric. The scenario and recovery
reports are its inputs. No live LLM was invoked, so model token use and
model-driven quality remain unverified. The local Docker integration test was
skipped; see the CI run for its separate Docker job. Other project gaps are in
[limitations](../docs/limitations.md).
