# Declarative simulation verification — 2026-10-17

The five public blueprints generated five deterministic scenarios covering
healthy operation, CPU saturation, memory growth, database failure, and
network latency. The generated JSONL matches the committed fixture.

| Check | Local result |
| --- | --- |
| Full suite | 108 tests discovered; 107 passed; 1 opt-in Docker test skipped locally |
| Blueprint and integration tests | Five scenario tests passed, including private-label rejection and permission enforcement |
| Synthetic load | 10/10 concurrent reads and 50/50 sequential reads returned consistent minute-10 metric and log snapshots |
| Agent observation | `SYN-002` at minute 5 showed rising CPU and a warning; at minute 15 it showed sustained CPU above 90% and a later failure log |

Run from the repository root:

```sh
.venv/bin/python -m scripts.generate_synthetic
.venv/bin/python -m scripts.run_synthetic SYN-002 --minute 5
.venv/bin/python -m scripts.run_synthetic SYN-002 --minute 15
.venv/bin/python -m scripts.validate_synthetic_load
.venv/bin/python -m unittest discover -s tests -p 'test_*.py' -q
```

`reports/reliability/synthetic_load.json` is a regenerated local artifact. Its
elapsed times vary by machine. The current implementation does not import
public datasets or run a Docker Compose fault environment; neither stage has
an evaluation result yet. See [simulation details](../docs/simulation.md).

Both the Python test job and Docker sandbox job passed for commit `65cd469` in
[GitHub Actions run 38984577737](https://github.com/karitselmuthu/Enterprise-Agent-Engineering-Evaluation/actions/runs/38984577737).
