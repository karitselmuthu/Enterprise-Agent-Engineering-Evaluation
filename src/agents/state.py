"""State for a single run."""
from dataclasses import dataclass, field
from typing import Any
from src.tools.executor import ToolResult
from src.evidence.schema import EvidenceCard, InvestigationFinding
from .investigation import InvestigationRecord

@dataclass
class AgentState:
    request: str
    tool_results: list[ToolResult] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    answer: str = ""
    evidence_cards: list[EvidenceCard] = field(default_factory=list)
    investigation: InvestigationRecord | None = None
    finding: InvestigationFinding | None = None
