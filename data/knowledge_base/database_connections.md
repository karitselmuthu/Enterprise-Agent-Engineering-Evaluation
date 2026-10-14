# Database connection failures

## Connection pool exhaustion
Inspect active, idle, and waiting database connections. Check slow queries,
pool limits, and leaked connections before increasing the pool size.

## Authentication failures
Check database credential rotation and authentication errors. Verify that the
application uses the intended secret version.
