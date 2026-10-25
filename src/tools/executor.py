"""Permission aware tool execution with an observed timeout."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from enum import Enum
import multiprocessing
from time import monotonic
from typing import Any
from src.policy.audit import AuditSink
from src.policy.engine import PolicyContext, PolicyDecision, decide
from .permissions import require_allowed
from .registry import ToolRegistry


class VerificationFailure(RuntimeError):
    """An executed side effect could not be confirmed."""


def _isolated_invoke(connection, tool, arguments):
    try:
        content = tool.handler(**arguments)
        if not tool.verifier(content):
            connection.send((False, "verification_failed", "Post-action verification failed"))
        else:
            connection.send((True, None, content))
    except Exception as exc:
        connection.send((False, "execution_failed", str(exc)))
    finally:
        connection.close()


class ToolStatus(str, Enum):
    SUCCESS = "SUCCESS"
    TIMEOUT = "TIMEOUT"
    TEMPORARY_FAILURE = "TEMPORARY_FAILURE"
    PERMISSION_DENIED = "PERMISSION_DENIED"
    INVALID_ARGUMENT = "INVALID_ARGUMENT"
    NOT_FOUND = "NOT_FOUND"
    POLICY_DENIED = "POLICY_DENIED"
    BUDGET_EXCEEDED = "BUDGET_EXCEEDED"
    MALFORMED_RESPONSE = "MALFORMED_RESPONSE"
    VERIFICATION_FAILED = "VERIFICATION_FAILED"
    EXECUTION_FAILED = "EXECUTION_FAILED"

@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    content: Any = None
    error: str | None = None
    error_code: str | None = None
    duration_ms: float = 0.0
    side_effect_verified: bool | None = None

    @property
    def status(self) -> ToolStatus:
        if self.ok:
            return ToolStatus.SUCCESS
        return {
            "timeout": ToolStatus.TIMEOUT,
            "mcp_unavailable": ToolStatus.TEMPORARY_FAILURE,
            "permission_denied": ToolStatus.PERMISSION_DENIED,
            "invalid_arguments": ToolStatus.INVALID_ARGUMENT,
            "invalid_timeout": ToolStatus.INVALID_ARGUMENT,
            "unknown_tool": ToolStatus.NOT_FOUND,
            "policy_denied": ToolStatus.POLICY_DENIED,
            "budget_exceeded": ToolStatus.BUDGET_EXCEEDED,
            "malformed_tool_response": ToolStatus.MALFORMED_RESPONSE,
            "verification_failed": ToolStatus.VERIFICATION_FAILED,
        }.get(self.error_code, ToolStatus.EXECUTION_FAILED)

class ToolExecutor:
    def __init__(self, registry: ToolRegistry, allowed: frozenset[str],
                 policy: PolicyContext | None = None, audit_sink: AuditSink | None = None):
        self.registry, self.allowed = registry, allowed
        self.policy = policy or PolicyContext()
        self.audit_sink = audit_sink

    def _audit(self, name: str, decision: PolicyDecision, result: ToolResult | None = None) -> None:
        if self.audit_sink is None:
            return
        self.audit_sink.append(
            actor_id=self.policy.actor_id, operation=name,
            environment=self.policy.environment,
            decision="allow" if decision.allowed else "deny",
            reason=decision.reason,
            approval_reference=decision.approval_reference,
            outcome=result.status.value if result is not None else None,
            duration_ms=result.duration_ms if result is not None else None)

    def _check(self, name: str, arguments: dict[str, Any],
               timeout_seconds: float) -> tuple[ToolResult | None, PolicyDecision]:
        decision = PolicyDecision(False, "preflight_denied")
        if timeout_seconds <= 0:
            return ToolResult(name, False, error="Timeout must be positive",
                              error_code="invalid_timeout"), decision
        try:
            tool = self.registry.get(name)
            require_allowed(name, self.allowed)
            tool.validate(arguments)
            decision = decide(tool, self.policy, arguments)
            if not decision.allowed:
                return ToolResult(name, False, error=f"Policy denied {name}: {decision.reason}",
                                  error_code="policy_denied"), decision
            if tool.side_effects and self.audit_sink is None:
                decision = PolicyDecision(False, "audit_sink_required")
                return ToolResult(name, False, error="Governance audit sink required",
                                  error_code="policy_denied"), decision
        except KeyError:
            return ToolResult(name, False, error=f"Unknown tool: {name}",
                              error_code="unknown_tool"), decision
        except PermissionError as exc:
            return ToolResult(name, False, error=str(exc), error_code="permission_denied"), decision
        except (ValueError, TypeError) as exc:
            return ToolResult(name, False, error=str(exc), error_code="invalid_arguments"), decision
        return None, decision

    def preflight(self, name: str, arguments: dict[str, Any],
                  timeout_seconds: float = 5.0) -> ToolResult | None:
        return self._check(name, arguments, timeout_seconds)[0]

    def _execute_isolated(self, tool, arguments: dict[str, Any],
                          timeout_seconds: float, started: float) -> ToolResult:
        try:
            context = multiprocessing.get_context("fork")
            parent, child = context.Pipe(duplex=False)
            process = context.Process(target=_isolated_invoke, args=(child, tool, arguments))
            process.start()
            child.close()
            try:
                if not parent.poll(timeout_seconds):
                    process.terminate()
                    process.join(1)
                    if process.is_alive():
                        process.kill()
                        process.join()
                    return ToolResult(tool.name, False,
                                      error=f"Tool timed out after {timeout_seconds}s",
                                      error_code="timeout",
                                      duration_ms=(monotonic() - started) * 1000)
                ok, code, content = parent.recv()
                process.join(1)
                return ToolResult(tool.name, ok, content=content if ok else None,
                                  error=None if ok else content, error_code=code,
                                  duration_ms=(monotonic() - started) * 1000,
                                  side_effect_verified=True if ok else None)
            finally:
                parent.close()
                if process.is_alive():
                    process.terminate()
                    process.join()
        except (OSError, EOFError, ValueError) as exc:
            return ToolResult(tool.name, False, error=str(exc),
                              error_code="execution_failed",
                              duration_ms=(monotonic() - started) * 1000)

    def execute(self, name: str, arguments: dict[str, Any],
                timeout_seconds: float = 5.0) -> ToolResult:
        started = monotonic()
        rejection, decision = self._check(name, arguments, timeout_seconds)
        try:
            self._audit(name, decision, rejection)
        except Exception:
            return ToolResult(name, False, error="Governance audit unavailable",
                              error_code="policy_denied")
        if rejection is not None:
            return rejection
        tool = self.registry.get(name)
        def finish(result: ToolResult) -> ToolResult:
            try:
                self._audit(name, decision, result)
            except Exception:
                return ToolResult(name, False, error="Governance audit unavailable after execution",
                                  error_code="execution_failed")
            return result
        if tool.side_effects:
            return finish(self._execute_isolated(tool, arguments, timeout_seconds, started))
        def invoke():
            try:
                content = tool.handler(**arguments)
                if tool.side_effects:
                    if not tool.verifier(content):
                        return False, VerificationFailure("Post-action verification failed")
                return True, content
            except Exception as exc:
                return False, exc

        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(invoke)
        try:
            ok, content = future.result(timeout=timeout_seconds)
            if not ok:
                return finish(ToolResult(name, False, error=str(content),
                                  error_code="timeout" if isinstance(content, TimeoutError)
                                  else "verification_failed" if isinstance(content, VerificationFailure)
                                  else "execution_failed",
                                  duration_ms=(monotonic() - started) * 1000))
            return finish(ToolResult(name, True, content=content,
                              duration_ms=(monotonic() - started) * 1000,
                              side_effect_verified=None))
        except FutureTimeout:
            future.cancel()
            return finish(ToolResult(name, False, error=f"Tool timed out after {timeout_seconds}s",
                              error_code="timeout",
                              duration_ms=(monotonic() - started) * 1000))
        except Exception as exc:
            return finish(ToolResult(name, False, error=str(exc), error_code="execution_failed",
                                     duration_ms=(monotonic() - started) * 1000))
        finally:
            # Running Python threads cannot be force-stopped. Only register trusted,
            # read-only handlers here; sandboxed processes arrive in phase 6.6.
            pool.shutdown(wait=False, cancel_futures=True)
