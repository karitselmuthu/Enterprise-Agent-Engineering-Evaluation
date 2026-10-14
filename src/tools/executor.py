"""Permission aware tool execution."""
from dataclasses import dataclass
from typing import Any
from .permissions import require_allowed
from .registry import ToolRegistry

@dataclass(frozen=True)
class ToolResult:
    name: str
    ok: bool
    content: Any = None
    error: str | None = None

class ToolExecutor:
    def __init__(self, registry: ToolRegistry, allowed: frozenset[str]):
        self.registry, self.allowed = registry, allowed

    def execute(self, name: str, arguments: dict[str, Any]) -> ToolResult:
        try:
            require_allowed(name, self.allowed)
            tool = self.registry.get(name)
            tool.validate(arguments)
            return ToolResult(name, True, tool.handler(**arguments))
        except (PermissionError, KeyError, ValueError, TypeError, FileNotFoundError) as exc:
            return ToolResult(name, False, error=str(exc))
