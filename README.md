# Enterprise-Agent-Engineering-Evaluation
# 1. Project overview
  Attribute	         Recommendation
  Repository name	   Enterprise_Agent_Evaluation
  Project type	     Enterprise AI Agent Engineering & Evaluation
  Architecture	     Modular, tool-driven agent framework
  Primary language	 Python
  LLM backend	       Small local model or configurable external provider
  API	               Proposed; not implemented
  CLI	               Python CLI
  Testing	           unittest
  Deployment	       Docker sandbox for generated code; service not deployed
  Development HW	   Apple Silicon Mac, 8 GB RAM
  Implementation 	   Incremental, experiment-driven
# Enterprise problem statement
  Enterprise organizations increasingly use AI agents to automate operational workflows, retrieve information, execute tools, and assist with technical investigations.
  However, building an AI agent is different from deploying a reliable enterprise agent.
  Common challenges include:
    - Unreliable tool execution.
    - Incorrect tool selection.
    - Loss of context during long conversations.
    - Inconsistent memory retrieval.
    - Poor handling of tool failures.
    - Unverified agent-generated recommendations.
    - Difficulty measuring agent performance.
    - Security risks from unrestricted tool execution.
# Proposed solution
  Build an Enterprise IT Operations Agent capable of investigating infrastructure and application incidents using controlled tools.
  The platform will demonstrate how agents plan actions, execute tools, maintain context, retrieve information, and produce recommendations.

# Example use case
  User request:
  "Investigate why the production application is experiencing high latency."

## Implementation status

Phase 6.1 provides a working tool-enabled incident agent with schema checks,
permissions, execution traces, timeout reporting, and a local Ollama adapter.
The default backend works offline with sample fixtures.

Run `PYTHONPATH=. python3 scripts/run_agent.py INC-001` and
`python3 -m unittest discover -s tests -p 'test_*.py' -v`.
See [Lecture 06](docs/lecture_06_agents.md) for phase details.

Phase 6.2 adds an MCP server and a permission-aware MCP client. Install the
project with `python3 -m pip install -e .` before running the MCP experiment.

Phase 6.3 adds SQLite-backed investigation memory. The memory experiment
shows a session resuming after the agent is reconstructed.

Phase 6.4 adds section-level TF-IDF search over five sample IT runbooks and
adds cited runbook guidance to MCP incident investigations.

Phase 6.5 adds a configurable context budget with conversation compaction and
preserved approved facts for long-running investigations.

Phase 6.6 adds a controlled coding-agent experiment that generates and tests a
Python log analyzer inside a resource-limited Docker container.

Phase 6.7 adds discoverable, permission-scoped skill manifests for incident
analysis and service health.

Lecture 7 starts with an optional local Ollama judge for answer assessment.
The mock backend remains the default for agent development and automated tests.
See [Lecture 07](docs/lecture_07_evaluation.md).

Lecture 7 also includes deterministic answer metrics, judge bias probes, agent
trajectory evaluation, and an offline benchmark. Run
`python3 scripts/run_evaluation.py` to produce a reproducible report.

The [verification strategy](docs/verification_strategy.md) defines test and
evidence requirements, including a proposed API contract. The API routes are
not implemented yet. A dated [verification snapshot](reports/verification_2026-10-14.md)
records current results and gaps.

## Simulation milestone

The [simulation layer](docs/simulation.md) adds 25 replayable incident scenarios,
a virtual clock, and five read-only infrastructure tools. Public observations
and private evaluation labels are stored separately. Run
`python3 -m scripts.run_simulation` for a baseline scenario report. This does
not replace the small deterministic unit-test fixtures.

The [scenario catalog](docs/scenario_catalog.md) lists the 25 distinct cases,
including pod crashes, cross-service network faults, concurrent incidents,
missing evidence, and healthy operation. Each private rubric records the
scenario name, affected service, expected findings, tools, and behavior. The
baseline report includes these rubrics alongside observed agent traces; tool
coverage does not imply the agent met every behavioral expectation.

The [data volume audit](docs/data_volume_audit.md) verifies the current five
dataset categories against the suggested initial sizes. None of those volume
targets has been reached; run `python3 -m scripts.audit_data` for current counts.

### Mode A replay validation

From the repository root, inspect the payment incident at three virtual times.
These commands wait for no wall-clock time and use only synthetic data:

```sh
python3 -m scripts.validate_mode_a --minute 15
python3 -m scripts.validate_mode_a --minute 25
python3 -m scripts.validate_mode_a --minute 35
```

At 10:15 UTC, expect CPU 82%, memory 73%, a connection warning, and advice to
gather evidence. At 10:25 UTC, expect CPU 97%, memory 89%, failed requests,
and escalation advice. At 10:35 UTC, expect a resolved status and recovery
monitoring advice. Each command prints the visible observations, selected
tools, and agent answer.

Run the automated acceptance check:

```sh
python3 -m scripts.validate_mode_a
python3 -m unittest tests.integration.test_mode_a_validation -v
```

The check exits nonzero on failure and writes
`reports/scenario_results/mode_a_validation.json`. It verifies event order,
future-event hiding, changing evidence and advice, recovery, and repeatability.
See [simulation details](docs/simulation.md) for the agent/data boundary.

### Mode B live polling and concurrency

Mode B publishes the same public scenario events at a configurable wall-clock
interval. Each poll receives a frozen event snapshot, so its three tool calls
observe the same virtual minute even when the publisher advances concurrently.
Run the default three-client check (about 0.35 seconds of scheduled events):

```sh
python3 -m scripts.validate_mode_b
python3 -m unittest tests.integration.test_mode_b_validation -v
```

To slow the publisher and change the polling load:

```sh
python3 -m scripts.validate_mode_b --interval 0.5 --poll-interval 0.1 --clients 8
```

`--interval` is seconds per scenario event; `--poll-interval` is seconds between
polls for each client. The command exits nonzero if publication, overlapping
polls, snapshot consistency, or final recovery checks fail. It writes every
poll's status, tool outcomes, and answer to
`reports/scenario_results/mode_b_validation.json`. A polling client can miss
short-lived intermediate states if its interval is too long; inspect the
report's observed minutes to see which states each client actually sampled.
The publisher paces deterministic synthetic events; it does not generate new
random incidents or connect to production infrastructure.
