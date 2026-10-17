"""Bounded, append-only record of a read-only investigation."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
from math import isfinite
from pathlib import Path
from time import monotonic
from typing import Any


@dataclass(frozen=True)
class InvestigationBudget:
    max_tool_calls: int = 30
    max_wall_time_seconds: float = 180.0

    def __post_init__(self) -> None:
        if (not isinstance(self.max_tool_calls, int)
                or isinstance(self.max_tool_calls, bool) or self.max_tool_calls < 1
                or not isinstance(self.max_wall_time_seconds, (int, float))
                or isinstance(self.max_wall_time_seconds, bool)
                or not isfinite(self.max_wall_time_seconds)
                or self.max_wall_time_seconds <= 0):
            raise ValueError("Investigation budget must be positive")


_TRANSITIONS = {
    "incident_received": {"observe", "final_diagnosis"},
    "observe": {"policy_check", "normalize_evidence", "final_diagnosis"},
    "policy_check": {"execute_read_action", "observe"},
    "execute_read_action": {"observe"},
    "normalize_evidence": {"verify", "final_diagnosis"},
    "verify": {"final_diagnosis"},
    "final_diagnosis": {"completed"},
    "completed": set(),
}


@dataclass
class InvestigationRecord:
    investigation_id: str
    budget: InvestigationBudget = field(default_factory=InvestigationBudget)
    phase: str = "incident_received"
    events: list[dict[str, Any]] = field(default_factory=list)
    tool_calls: int = 0
    agent_version: str = "simulation-investigator-v1"
    _started: float = field(default_factory=monotonic, repr=False)

    def __post_init__(self) -> None:
        self.record("investigation_started", agent_version=self.agent_version)

    def record(self, kind: str, **details: Any) -> None:
        self.events.append({"investigation_id": self.investigation_id,
                            "event_id": f"{self.investigation_id}:{len(self.events) + 1}",
                            "sequence_number": len(self.events) + 1,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "phase": self.phase, "kind": kind, **details})

    def transition(self, phase: str) -> None:
        if phase not in _TRANSITIONS[self.phase]:
            raise ValueError(f"Illegal transition: {self.phase} -> {phase}")
        self.phase = phase
        self.record("phase_entered")

    def reserve_tool_call(self) -> bool:
        if (self.tool_calls >= self.budget.max_tool_calls
                or monotonic() - self._started >= self.budget.max_wall_time_seconds):
            self.record("budget_exceeded", tool_calls=self.tool_calls)
            return False
        self.tool_calls += 1
        return True

    def write_jsonl(self, path: str | Path) -> None:
        """Create an immutable run artifact; refuse to overwrite an existing file."""
        with Path(path).open("x", encoding="utf-8") as output:
            for event in self.events:
                output.write(json.dumps(event, sort_keys=True) + "\n")
