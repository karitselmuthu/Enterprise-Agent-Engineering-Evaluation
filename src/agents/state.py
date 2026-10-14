"""State for a single run."""
from dataclasses import dataclass, field
from src.tools.executor import ToolResult

@dataclass
class AgentState:
    incident_id: str
    tool_results: list[ToolResult] = field(default_factory=list)
    answer: str = ""
