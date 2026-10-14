"""Bounded in-process state for an investigation session."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ShortTermMemory:
    session_id: str
    current_task: str = ""
    conversation: list[dict[str, str]] = field(default_factory=list)
    recent_tool_results: list[dict[str, Any]] = field(default_factory=list)
    max_items: int = 20

    def add_message(self, role: str, content: str) -> None:
        if role not in {"user", "assistant"}:
            raise ValueError("Invalid conversation role")
        self.conversation.append({"role": role, "content": content})
        self.conversation = self.conversation[-self.max_items:]

    def add_tool_result(self, name: str, ok: bool, content: Any) -> None:
        self.recent_tool_results.append({"name": name, "ok": ok, "content": content})
        self.recent_tool_results = self.recent_tool_results[-self.max_items:]
