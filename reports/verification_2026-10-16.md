# Verification snapshot — 2026-10-16

This snapshot records the initial four-level agent validation work. It does
not establish production accuracy or capacity.

| Check | Local result |
| --- | --- |
| Runtime | Python 3.14.7, `mcp` 2.3.0, `pydantic` 2.14.1 |
| Full unit, integration, and evaluation suite | 100 tests discovered; 99 passed; 1 opt-in Docker test skipped locally |
| Scenario foundation gate | 25/25 cases selected required tool names; 25/25 retrieved expected visible evidence |
| Cause support proxy | 0.00 exact phrase rate on causal cases; this is not semantic accuracy |
| Recommendation cue | 0.16 of cases include a case-specific cue in the final recommendation; this is not semantic accuracy |
| Reliability workload | 10 synchronized concurrent investigations, 50 sequential requests, and 5 identical repeats passed |
| Failure probes | Delayed tool timeout, MCP outage and recovery, malformed tool content, and bounded agent timeout passed |
| Mode A and Mode B | Both validation commands passed locally |
| Docker | Local daemon unavailable; CI Docker sandbox job passed |

Run from the repository root:

```sh
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -v
.venv/bin/python -m scripts.validate_scenarios
.venv/bin/python -m scripts.validate_reliability
.venv/bin/python -m scripts.validate_mode_a
.venv/bin/python -m scripts.validate_mode_b
```

`scenario_validation.json` records each case's tool, evidence, cause proxy,
and recommendation cue result. The first two checks form the CI gate; the
last two expose baseline quality gaps for later agent improvements. Tool order
is unconstrained. `reliability.json` records workload counts, checks, and
observed local timings. The workload uses deterministic synthetic data and
is too small to support a throughput claim.

The API endpoints, real infrastructure connectors, semantic judge calibration,
and hosted or local model quality remain unverified. The existing broader
project limitations remain in [limitations](../docs/limitations.md).

Both the Python test job and Docker sandbox job passed for the validation
implementation in [GitHub Actions run 38866613054](https://github.com/karitselmuthu/Enterprise-Agent-Engineering-Evaluation/actions/runs/38866613054).
