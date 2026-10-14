"""Deterministic token estimates and budget validation."""

from dataclasses import dataclass
import re

TOKEN = re.compile(r"\w+|[^\w\s]", re.UNICODE)


class ContextBudgetExceeded(ValueError):
    pass


class TokenCounter:
    """Model-agnostic estimate; providers may count tokens differently."""

    def count(self, text: str) -> int:
        return len(TOKEN.findall(text))

    def truncate(self, text: str, limit: int) -> str:
        if limit < 0:
            raise ValueError("limit must be nonnegative")
        matches = list(TOKEN.finditer(text))
        if len(matches) <= limit:
            return text
        if limit == 0:
            return ""
        return text[:matches[limit - 1].end()].rstrip() + " …"


@dataclass(frozen=True)
class ContextBudget:
    total_tokens: int = 1024
    reserved_output_tokens: int = 256
    max_tool_output_tokens: int = 96

    def __post_init__(self) -> None:
        if (self.total_tokens <= 0 or self.reserved_output_tokens < 0
                or self.reserved_output_tokens >= self.total_tokens
                or self.max_tool_output_tokens < 0):
            raise ValueError("Invalid context budget")

    @property
    def input_tokens(self) -> int:
        return self.total_tokens - self.reserved_output_tokens
