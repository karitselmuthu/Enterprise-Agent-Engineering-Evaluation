# Optional data and live setup verification — 2026-10-17

Stage 2 now has a field-mapped JSONL log import command for data supplied by a
project user. No public dataset was selected or imported. The command validates
UTC timestamps and severity and writes normalized observations outside tracked
fixtures. It does not create an incident timeline or ground-truth labels.

Stage 3 now has an opt-in local Compose profile with one Python HTTP service
and SQLite. Its fault-control route can switch healthy, database-failure, and
recovered modes. The baseline agent reads observations through the existing
incident, metrics, and logs tool contracts. This is a local prototype, not a
production integration or a scored evaluation environment.

| Check | Local result |
| --- | --- |
| Full suite | 113 tests discovered; 111 passed; 2 opt-in Docker tests skipped locally |
| Data import | Valid mapping normalized and ordered logs; invalid timestamps and severities rejected |
| Live HTTP integration | Healthy → database failure → recovery passed through standard agent tools; invalid fault mode rejected |
| Compose structure | `docker compose --profile live-demo config --quiet` passed |
| Local container smoke | Not run: Docker daemon unavailable on this machine |

Run the optional container smoke test with a working Docker daemon:

```sh
RUN_LIVE_COMPOSE=1 python3 -m unittest tests.integration.test_live_compose -v
```

The CI Docker job runs that test separately. No Stage 2 dataset quality or
Stage 3 agent accuracy score is reported.
