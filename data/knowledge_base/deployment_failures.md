# Application deployment failures

## Failed rollout
Inspect deployment events, health checks, and image pull errors. Compare the
new revision with the last healthy version before a rollback.

## Configuration regression
Diff environment variables, secrets references, and feature flags against the
previous release. Restore only the confirmed faulty setting.
