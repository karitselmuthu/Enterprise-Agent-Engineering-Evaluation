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
