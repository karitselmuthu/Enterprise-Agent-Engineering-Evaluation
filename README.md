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

Investigate why the production application is experiencing high latency. The
default agent reads controlled incident observations, selects permitted tools,
and reports the evidence it found. The default backend is deterministic and
runs offline.

## Start here

From the repository root, use Python 3.11 or newer:

    python3 -m pip install -e .
    python3 scripts/run_agent.py INC-001
    python3 -m unittest discover -s tests -p 'test_*.py' -v

The installation uses the dependencies declared in [pyproject.toml](pyproject.toml).
A local Ollama backend is optional; the mock backend is the default. Docker is
needed only for the coding sandbox and the optional live demo.

## What is implemented

| Area | Current capability | Where to look |
| --- | --- | --- |
| Lecture 6.1–6.2 | Tool selection, schemas, permissions, traces, and MCP discovery/invocation | [Agent guide](docs/lecture_06_agents.md) |
| Lecture 6.3–6.5 | SQLite investigation memory, TF-IDF runbook retrieval, and context budgeting | [Architecture](docs/architecture.md) |
| Lecture 6.6–6.7 | Docker-restricted code experiment and permission-scoped skills | [Agent guide](docs/lecture_06_agents.md) |
| Lecture 7.1–7.5 | Optional local judge, deterministic metrics, bias probes, trajectory evaluation, and offline benchmark | [Evaluation guide](docs/lecture_07_evaluation.md) |
| Simulation | Virtual-clock replay, live polling of synthetic events, and standard incident/metric/log tool adapters | [Simulation guide](docs/simulation.md) |
| Architecture review improvements | Host policy gate, read-only investigation lifecycle and budget, source-linked evidence cards, event records, and repeated-run process checks | [Structure comparison and scope](docs/architecture_improvement_comparison.md) |
| Governance foundation | Scoped approval checks, isolated mutating tool execution, and HMAC-chained local audit events in the standard tool executor | [Implementation and limits](docs/governance_hardening.md); [architecture status](docs/Enterprise%20AI%20Agent%20Governance%20Architecture.md) |

The [implementation maturity review](reports/implementation_maturity_review_2026-10-17.md)
checks the code paths against the architecture claims, records local test and
Ollama results, and lists the gaps to close before treating this as a
production-ready agent.

The [experiment scripts](experiments/) demonstrate each lecture phase. The
HTTP API and unified CLI are proposed interfaces; they are not runnable yet.
See the [verification strategy](docs/verification_strategy.md) for their
planned contracts.

## Simulation and data

The 25-case replay dataset is in
[data/simulation/scenarios.jsonl](data/simulation/scenarios.jsonl). Private
evaluation labels are stored separately in
[data/evaluation_datasets/simulation_ground_truth.jsonl](data/evaluation_datasets/simulation_ground_truth.jsonl).
The agent receives time-bounded observations through its normal tool executor,
not those labels.

Five additional synthetic blueprints cover healthy operation, CPU saturation,
memory growth, database failure, and network latency. Regenerate their public
observations and compare an early and late investigation:

    python3 -m scripts.generate_synthetic
    python3 -m scripts.run_synthetic SYN-002 --minute 5
    python3 -m scripts.run_synthetic SYN-002 --minute 15

The blueprints in [simulation/scenarios](simulation/scenarios/) use the JSON
subset of YAML, so they require no YAML package. The generated file is
[data/synthetic/scenarios.jsonl](data/synthetic/scenarios.jsonl).

### Stage 2: bring your own logs

No public dataset is bundled. When you choose data, edit the
[field mapping](configs/public_logs.example.json) for your source JSONL fields
and run:

    python3 -m scripts.import_public_logs path/to/logs.jsonl \
      --mapping configs/public_logs.example.json \
      --output data/imported/my_dataset/logs.jsonl

The importer validates UTC timestamps, service, severity, and message, then
writes normalized observations to a Git-ignored directory. It does not create
incident timelines or root-cause labels. Source-specific parsing and evaluation
labels remain work for the dataset you choose.

### Stage 3: optional local fault demo

The [Compose profile](compose.yaml) starts one lightweight Python HTTP service
with SQLite. It is a user option, not part of the default agent workflow. With
a working Docker daemon:

    docker compose --profile live-demo up --build -d
    python3 -m scripts.run_live_demo
    python3 -m scripts.inject_live_fault database_failure
    python3 -m scripts.run_live_demo
    python3 -m scripts.inject_live_fault recovered
    python3 -m scripts.run_live_demo
    docker compose --profile live-demo down

The host port is bound to 127.0.0.1:8765. The agent reads live incident,
metrics, and logs through the same tool names and schemas as replay. The named
SQLite volume persists; use docker compose --profile live-demo down -v only
when you want to remove its demo data. This is a local prototype, not a
production integration or a scored live evaluation.

## Verify behavior

### Test and scenario map

The full `unittest` discovery command in **Start here** runs test files in
`tests/unit`, `tests/integration`, `tests/scenarios`, `tests/evaluation`, and
`tests/load`. The [CI workflow](.github/workflows/ci.yml) runs that suite and
the validation scripts below. The table shows where to find each scenario
family and how to run a focused check from the repository root.

| Scenario family | What is checked | Focused command or catalog |
| --- | --- | --- |
| Core agent and tools | Selection, argument schemas, allowlists, failures, timeouts, context, skills, and coding-agent controls | `python3 -m unittest discover -s tests/unit -v` |
| Replay incidents | All 25 `SIM-001`–`SIM-025` cases, including healthy, missing data, denied tools, recovery, conflicting signals, and multiple incidents | [All 25 cases and expected evidence](docs/scenario_catalog.md); `python3 -m scripts.validate_scenarios` |
| Database latency branches | `SIM-004` with complete evidence, early or stale metrics, missing metrics, tool timeout, misleading log, and malformed sample | `python3 -m unittest tests.scenarios.test_database_latency -v`; `python3 -m scripts.validate_database_latency` |
| Synthetic blueprints | Five additional `SYN` cases at different virtual times, plus permission and fixture validation | `python3 -m unittest tests.scenarios.test_synthetic_blueprints -v` |
| Governance | Default denial, scoped and expired approvals, wrong target, audit integrity, verifier failure, and mutation timeout; several planned `GOV-001`–`GOV-015` cases remain partial or pending | [GOV case-by-case status](docs/Enterprise%20AI%20Agent%20Governance%20Architecture.md#8-governance-scenario-coverage); `python3 -m unittest tests.unit.test_governance tests.unit.test_policy_and_investigation tests.scenarios.test_governance_scenario -v` |
| Agent integrations | MCP allowlist and failures, SQLite resume, retrieval citations, evidence budgets, live polling, and the local HTTP demo | `python3 -m unittest discover -s tests/integration -v` |
| Evaluation and reliability | Offline judge fixtures, bias probes, benchmark behavior, process and operational metrics, bounded investigations, and concurrent/sequential load | `python3 -m unittest discover -s tests/evaluation -v`; `python3 -m unittest discover -s tests/load -v` |
| Optional Docker paths | Generated-code sandbox and the Compose fault flow | `RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_coding_sandbox -v`; `RUN_LIVE_COMPOSE=1 python3 -m unittest tests.integration.test_live_compose -v` |

Install the project first with `python3 -m pip install -e .`; MCP integration
tests need the declared `mcp` dependency. The local HTTP integration test
binds a loopback port, so a sandbox that blocks socket binding cannot run the
full suite. The Docker tests need a working daemon and their environment
flags; they are skipped in ordinary discovery and run separately in CI.

These tests verify local behavior and deterministic fixtures. The 25 replay
cases and five synthetic blueprints are committed data; the `GOV` IDs are a
coverage plan with explicit implemented, partial, and pending statuses in the
architecture document. Neither set is a production safety or diagnosis
accuracy certification.

### Validation scripts

The main checks run from the repository root:

    python3 -m scripts.validate_mode_a
    python3 -m scripts.validate_mode_b
    python3 -m scripts.validate_scenarios
    python3 -m scripts.validate_database_latency
    python3 -m scripts.validate_reliability
    python3 -m scripts.validate_process --trials 5
    python3 -m scripts.report_operational_metrics
    python3 -m scripts.validate_synthetic_load
    python3 scripts/run_evaluation.py

The scenario gate checks tool selection and visible evidence across 25 cases.
The [database latency scenario report](reports/database_latency_scenario_2026-10-17.md)
shows the full `SIM-004` workflow and outcomes for missing database metrics,
tool timeout, and misleading logs. The command writes detailed checks to
`reports/scenario_results/database_latency.json`.
The process check repeats each case and verifies lifecycle milestones, budget
enforcement, and evidence references. Its pass rates are workflow proxies, not
root-cause accuracy. See the [architecture review comparison](docs/architecture_improvement_comparison.md)
for changed paths, recommended paths, and deferred work.
The [governance hardening guide](docs/governance_hardening.md) describes scoped
approvals, isolated mutating calls, durable audit records, and their limits.
The reliability workload includes concurrent and sequential investigations,
timeouts, malformed responses, and temporary MCP failure. Generated JSON
reports go under reports/. The [operational metric definitions](docs/verification_strategy.md#operational-metric-contract)
explain each denominator. Task completion, semantic root-cause accuracy,
claim-level groundedness, hallucination rate, and token use remain unmeasured
in the mock simulation baseline.

See the [latest verification records](reports/verification_2026-10-17.md),
[synthetic simulation record](reports/simulation_verification_2026-10-17.md),
and [optional setup record](reports/optional_data_live_setup_2026-10-17.md).
The [data volume audit](docs/data_volume_audit.md) records current counts
against the larger suggested inventory, metric, log, incident, and knowledge
base targets.

## Repository map and reserved locations

| Path | Purpose |
| --- | --- |
| [src/](src/) | Implemented agent, evidence, policy, tools, MCP, memory, retrieval, context, coding, skills, and evaluation packages. Empty __init__.py files mark importable packages. |
| [simulation/](simulation/) | Replay and live simulation engines, generators, importers, and adapters. The live demo has its own Dockerfile under simulation/live_stack/. |
| [data/](data/) | Tracked teaching fixtures and scenario labels. data/imported/ is reserved for your own datasets and ignored by Git. |
| [experiments/](experiments/) | Runnable Lecture 6 and 7 demonstrations. |
| [scripts/](scripts/) | Current command-line entry points for agents, generation, imports, and verification. |
| [tests/](tests/) | Unit, integration, scenario, evaluation, and local load checks. |
| [reports/](reports/) | Dated evidence records and generated JSON reports; scripts create output directories when needed. |
| [configs/](configs/) | Active public-log field-mapping example; other configuration files will be added when their consumers exist. |
| [api/](api/) | Reserved for the future HTTP routes and schemas described in the verification strategy. No API code is shipped yet. |
| [cli/](cli/) | Reserved for a future unified CLI; use scripts/ today. |

See [current limitations](docs/limitations.md) before interpreting mock
results as production reliability or incident diagnosis accuracy.
