"""Compact older turns and large tool results."""

import json
from typing import Any

from .token_budget import TokenCounter


def summarize_conversation(messages: list[dict[str, str]], counter: TokenCounter,
                           max_tokens: int = 96) -> str:
    if not messages or max_tokens <= 0:
        return ""
    lines = []
    for message in messages:
        role = message.get("role", "unknown")
        excerpt = counter.truncate(message.get("content", ""), 18)
        lines.append(f"{role}: {excerpt}")
    return counter.truncate("Earlier conversation: " + " | ".join(lines), max_tokens)


def truncate_tool_output(result: dict[str, Any], counter: TokenCounter,
                         max_tokens: int) -> str:
    data = json.dumps(result.get("content"), ensure_ascii=False, sort_keys=True)
    return f"{result.get('name', 'tool')} ({'ok' if result.get('ok') else 'error'}): " + (
        counter.truncate(data, max_tokens))
