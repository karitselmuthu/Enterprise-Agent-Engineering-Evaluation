"""Response backend interface."""
from typing import Any, Protocol
from src.tools.executor import ToolResult

class Backend(Protocol):
    def select_tool(self, request: str, tools: list[dict[str, Any]]
                    ) -> tuple[str, dict[str, Any]] | None: ...
    def interpret(self, request: str, result: ToolResult) -> str: ...
