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
