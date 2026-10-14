# Lecture 06: Agent engineering

## 6.1 Tool calling

The starter incident agent validates tool arguments, enforces a deny-by-default
allowlist, records tool results, and builds an offline deterministic answer.

Run: `PYTHONPATH=. python3 scripts/run_agent.py INC-001`

The planner currently uses one fixed read-only tool call.
