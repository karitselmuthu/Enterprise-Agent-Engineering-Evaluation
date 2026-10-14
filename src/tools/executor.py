"""Permission aware tool execution with an observed timeout."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from time import monotonic
from typing import Any
from .permissions import require_allowed
from .registry import ToolRegistry

@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    content: Any = None
    error: str | None = None
    error_code: str | None = None
    duration_ms: float = 0.0

class ToolExecutor:
    def __init__(self, registry: ToolRegistry, allowed: frozenset[str]):
        self.registry, self.allowed = registry, allowed

    def execute(self, name: str, arguments: dict[str, Any],
                timeout_seconds: float = 5.0) -> ToolResult:
        started = monotonic()
        if timeout_seconds <= 0:
            return ToolResult(name, False, error="Timeout must be positive",
                              error_code="invalid_timeout")
        try:
            tool = self.registry.get(name)
            require_allowed(name, self.allowed)
            tool.validate(arguments)
        except KeyError:
            return ToolResult(name, False, error=f"Unknown tool: {name}",
                              error_code="unknown_tool")
        except PermissionError as exc:
            return ToolResult(name, False, error=str(exc), error_code="permission_denied")
        except (ValueError, TypeError) as exc:
            return ToolResult(name, False, error=str(exc), error_code="invalid_arguments")
        def invoke():
            try:
                return True, tool.handler(**arguments)
            except Exception as exc:
                return False, exc

        pool = ThreadPoolExecutor(max_workers=1)
        future = pool.submit(invoke)
        try:
            ok, content = future.result(timeout=timeout_seconds)
            if not ok:
                return ToolResult(name, False, error=str(content),
                                  error_code="timeout" if isinstance(content, TimeoutError)
                                  else "execution_failed",
                                  duration_ms=(monotonic() - started) * 1000)
            return ToolResult(name, True, content=content,
                              duration_ms=(monotonic() - started) * 1000)
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
