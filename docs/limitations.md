# Current limitations

- The default tool selector is deterministic. The Ollama adapter has mocked
  protocol tests, but no live-model quality evaluation yet.
- The phase 6.1 thread timeout reports a timeout but cannot stop a running
  Python handler. Only trusted read-only handlers are registered.
- MCP tools currently read local fixtures over stdio. There is no remote
  authentication, production infrastructure adapter, or server deployment.
- SQLite memory is local to one machine. An approved fact is trusted because
  the caller marks it approved; there is no reviewer workflow.
- The five runbooks are teaching fixtures. TF-IDF matches words, so it may
  miss synonyms or rank incidental word overlap. Retrieved text should be
  checked against live incident evidence before operational changes.
- Context token counts are model-agnostic estimates. A provider-specific
  tokenizer is needed before treating the configured budget as a hard model
  context-window guarantee.
- Coding-agent static checks reduce mistakes but are not an isolation
  boundary. Docker is required; the agent refuses execution if its daemon or
  local Python image is unavailable. The Docker integration test runs in CI.
- Skill manifests support string inputs and text or JSON outputs. Skill authors
  must be trusted to write instructions, and new MCP tools still require an
  explicit host policy grant.
- Lecture 7 judge protocols are covered with injected responses, but no live
  local or hosted model quality results are available. The mock benchmark is
  deterministic and small, so its pass rate is not a production estimate.
- The proposed HTTP API and metrics endpoint are not implemented yet. See the
  verification strategy for their future acceptance checks.
- The 25-scenario replay dataset is synthetic. Most cases have four timestamps;
  the payment case has eight. Its label separation is an architectural boundary, not a process
  isolation boundary. The baseline investigator reports observations but does
  not reliably identify root causes; the literal phrase metric is not a
  semantic accuracy measure.
