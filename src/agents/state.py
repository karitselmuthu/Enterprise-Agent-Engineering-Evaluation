"""State for a single run."""
from dataclasses import dataclass, field
from typing import Any
from src.tools.executor import ToolResult

@dataclass
class AgentState:
    request: str
    tool_results: list[ToolResult] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
