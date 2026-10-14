# Lecture 06: Agent engineering

## 6.1 Tool calling

The incident agent asks a backend to select a tool from declared schemas,
validates arguments, enforces a deny-by-default allowlist, records a trace,
and interprets tool results. The default backend is deterministic and offline.
Pass `--ollama-model MODEL` to use a running local Ollama model for tool
selection and interpretation.

Run: `PYTHONPATH=. python3 scripts/run_agent.py INC-001`

Tool calls have a five-second observed timeout. A timed-out Python handler
continues in its worker thread until it returns; only trusted read-only tools
belong in this registry.

## 6.2 Model Context Protocol

The MCP server exposes incident and service health tools through the official
Python SDK. The client discovers tools, restricts them to an allowlist, invokes
the selected tool, and reads its structured response. The SDK validates
arguments and reports server tool errors.

Run `.venv/bin/python experiments/lecture_06/02_mcp.py` to exercise a real
stdio server subprocess. The in-memory MCP connection is used in tests.

## 6.3 Agent memory

`ShortTermMemory` keeps bounded conversation turns, the current task, and
recent tool results. `LongTermMemory` stores investigations, notes, approved
facts, and tool results in SQLite. A new `StatefulIncidentAgent` instance can
resume an existing session and use its previous incident ID for follow-ups.
Only explicitly approved facts are added to a new answer.
The same store also wraps the MCP agent through `StatefulMCPIncidentAgent`.

Run `PYTHONPATH=. .venv/bin/python experiments/lecture_06/03_memory.py`.

## 6.4 Retrieval

Five short IT runbooks are indexed by section with TF-IDF and cosine
similarity. `RetrievalIncidentAgent` combines MCP tool results with the
request, retrieves the highest-ranked sections, includes their source and
heading in the answer, and saves that answer to SQLite. Only positive-score
sections are returned. Embedding retrieval is an interface for later work,
not an active backend.

Run `PYTHONPATH=. .venv/bin/python experiments/lecture_06/04_retrieval.py`.

## 6.5 Context compaction

`ContextManager` estimates tokens, reserves response capacity, summarizes
older turns, truncates recent tool output, and removes optional context until
the input fits. The current request and explicitly approved facts are pinned;
an overlong critical section raises `ContextBudgetExceeded`. The integrated
`ContextAwareIncidentAgent` sends this bounded prompt to the MCP agent and
then retrieves runbook guidance.

Run `PYTHONPATH=. .venv/bin/python experiments/lecture_06/05_context_compaction.py`.

## 6.6 Coding agents

`LogAnalysisCodeAgent` generates a Python log analyzer, statically checks its
AST, executes it against supplied logs inside a Docker container, and runs a
second known-result fixture in another container. The sandbox has no network,
a read-only root, a read-only script mount, a non-root user, dropped
capabilities, CPU, memory, PID, time, input, and output limits. The image must
already exist locally; the agent fails closed if Docker is unavailable.
The default generator is a deterministic template; set `OLLAMA_MODEL` to use
a local model for source generation through the same validation and sandbox.

Prepare with `docker pull python:3.12-alpine`, then run
`PYTHONPATH=. .venv/bin/python experiments/lecture_06/06_coding_agent.py`.
CI runs the real Docker integration test.

## 6.7 Skills

Each `skill.json` declares its purpose, named string inputs, permitted MCP
tools, execution instructions, output format, and error behavior. The loader
discovers skill directories; the runner validates inputs and intersects skill
permissions with host policy before invoking the MCP agent. The incident
analysis and service health manifests demonstrate reusable capabilities.
To add a skill, create a child directory under `src/skills/` with a
`skill.json` following either example, then allow its tools in the host
policy passed to `SkillRunner`.

Run `PYTHONPATH=. .venv/bin/python experiments/lecture_06/07_skills.py`.
