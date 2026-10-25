# Governance hardening

`ToolExecutor` keeps the existing agent flow. A mutation requires an explicit
allowlist entry, tool scopes, `allow_mutations`, actor identity, a verifier, and
an `AuditSink`. High risk mutations, and production mutations whose metadata
requires approval, also require an `Approval` matching the actor, tool name,
resource argument, canonical argument digest, and unexpired UTC timestamp.
The old `approved_tools` field no longer grants approval.

The host creates approvals after authenticating the actor and reviewer. Treat
`PolicyContext` and `Approval` as trusted host inputs; a model or tool must not
construct them. `resource_argument` must identify the resource in the tool's
validated arguments. Approval references identify the decision for later
review. The current implementation does not issue, sign, revoke, or consume
approvals and does not provide a human approval workflow. An exact approved
request can be repeated until expiry; callers needing one-time approval must
add a transactional approval store before enabling operational write tools.

The audit sink writes an HMAC chained JSONL file with policy version, actor,
operation, environment, decision, reason, approval reference, outcome status,
and duration. It omits arguments, prompts, output content, and exception text.
The caller must supply a secret key from outside the repository, protect it
separately, restrict access to the audit file, and export or anchor chain heads
off-host. Verification detects edits to retained records, but cannot detect
full-file deletion or replacement without an external anchor. Appends are
locked and synced to disk. A mutation is denied when its audit sink is absent
or the pre-execution append fails. An audit write failure after execution is
reported as an execution failure, but cannot undo an already completed change.

Mutating handlers and their verifiers run in a forked process. A timeout
terminates that process and then kills it if necessary. This prevents Python
code in that child from continuing after the timeout. It cannot roll back a
change already sent to an external system, and it does not guarantee that a
child's own descendant processes or remote operations stop. Production
adapters should pass deadlines and idempotency keys downstream and verify
remote state independently. `fork` is POSIX specific; non-POSIX hosts fail
closed for mutations. Read-only handlers still use the existing thread pool.

Threat scenarios covered by tests include a stolen approval for another
actor, operation, resource, or argument set; an expired approval; a legacy
name-only approval; a missing audit sink; modified audit records; and a
mutating handler that attempts a delayed write after a timeout.
