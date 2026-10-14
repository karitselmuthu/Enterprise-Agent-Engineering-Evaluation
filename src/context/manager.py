"""Assemble a bounded model prompt while pinning approved facts."""

from dataclasses import dataclass
from typing import Any

from .compaction import summarize_conversation, truncate_tool_output
from .token_budget import ContextBudget, ContextBudgetExceeded, TokenCounter


@dataclass(frozen=True)
class ManagedContext:
    prompt: str
    estimated_tokens: int
    input_budget: int
    summarized_turns: int
    included_tool_results: int


class ContextManager:
    def __init__(self, budget: ContextBudget | None = None,
                 counter: TokenCounter | None = None):
        self.budget = budget or ContextBudget()
        self.counter = counter or TokenCounter()

    def build(self, request: str, conversation: list[dict[str, str]],
              tool_results: list[dict[str, Any]],
              critical_facts: list[str]) -> ManagedContext:
        if not request.strip():
            raise ValueError("request is required")
        essential = ["Current request: " + request]
        if critical_facts:
            essential.append("Approved critical facts: " + " | ".join(critical_facts))
        if self.counter.count("\n".join(essential)) > self.budget.input_tokens:
            raise ContextBudgetExceeded("Current request and critical facts exceed input budget")

        older, recent = conversation[:-4], conversation[-4:]
        summary = summarize_conversation(older, self.counter)
        recent_lines = [f"{item['role']}: {item['content']}" for item in recent]
        tool_lines = [truncate_tool_output(item, self.counter,
                                           self.budget.max_tool_output_tokens)
                      for item in tool_results[-4:]]

        def render() -> str:
            parts = list(essential)
            if summary:
                parts.append(summary)
            if recent_lines:
                parts.append("Recent conversation:\n" + "\n".join(recent_lines))
            if tool_lines:
                parts.append("Recent tool results:\n" + "\n".join(tool_lines))
            return "\n\n".join(parts)

        # Preserve the current request and approved facts. Remove optional
        # material in order of least useful for the next decision.
        while self.counter.count(render()) > self.budget.input_tokens:
            if tool_lines:
                tool_lines.pop(0)
            elif len(recent_lines) > 1:
                recent_lines.pop(0)
            elif summary:
                summary = self.counter.truncate(summary,
                                                max(0, self.counter.count(summary) - 8))
            elif recent_lines:
                recent_lines.pop(0)
            else:
                raise ContextBudgetExceeded("Cannot fit context in budget")
        prompt = render()
        return ManagedContext(prompt, self.counter.count(prompt),
                              self.budget.input_tokens, len(older) if summary else 0,
                              len(tool_lines))
