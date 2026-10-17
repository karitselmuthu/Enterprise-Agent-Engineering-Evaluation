"""Permission aware tool execution with an observed timeout."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from enum import Enum
from time import monotonic
from typing import Any
from src.policy.engine import PolicyContext, authorize
from .permissions import require_allowed
from .registry import ToolRegistry


class VerificationFailure(RuntimeError):
    """An executed side effect could not be confirmed."""


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
                 policy: PolicyContext | None = None):
        self.registry, self.allowed = registry, allowed
        self.policy = policy or PolicyContext()

    def preflight(self, name: str, arguments: dict[str, Any],
                  timeout_seconds: float = 5.0) -> ToolResult | None:
        if timeout_seconds <= 0:
            return ToolResult(name, False, error="Timeout must be positive",
                              error_code="invalid_timeout")
        try:
            tool = self.registry.get(name)
            require_allowed(name, self.allowed)
            try:
                authorize(tool, self.policy)
            except PermissionError as exc:
                return ToolResult(name, False, error=str(exc), error_code="policy_denied")
            tool.validate(arguments)
        except KeyError:
            return ToolResult(name, False, error=f"Unknown tool: {name}",
                              error_code="unknown_tool")
        except PermissionError as exc:
            return ToolResult(name, False, error=str(exc), error_code="permission_denied")
        except (ValueError, TypeError) as exc:
            return ToolResult(name, False, error=str(exc), error_code="invalid_arguments")
        return None

    def execute(self, name: str, arguments: dict[str, Any],
                timeout_seconds: float = 5.0) -> ToolResult:
        started = monotonic()
        rejection = self.preflight(name, arguments, timeout_seconds)
        if rejection is not None:
            return rejection
        tool = self.registry.get(name)
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
                return ToolResult(name, False, error=str(content),
                                  error_code="timeout" if isinstance(content, TimeoutError)
                                  else "verification_failed" if isinstance(content, VerificationFailure)
                                  else "execution_failed",
                                  duration_ms=(monotonic() - started) * 1000)
            return ToolResult(name, True, content=content,
                              duration_ms=(monotonic() - started) * 1000,
                              side_effect_verified=True if tool.side_effects else None)
        except FutureTimeout:
            future.cancel()
            return ToolResult(name, False, error=f"Tool timed out after {timeout_seconds}s",
                              error_code="timeout",
                              duration_ms=(monotonic() - started) * 1000)
        except Exception as exc:
            return ToolResult(name, False, error=str(exc), error_code="execution_failed",
                              duration_ms=(monotonic() - started) * 1000)
        finally:
            # Running Python threads cannot be force-stopped. Only register trusted,
            # read-only handlers here; sandboxed processes arrive in phase 6.6.
            pool.shutdown(wait=False, cancel_futures=True)
