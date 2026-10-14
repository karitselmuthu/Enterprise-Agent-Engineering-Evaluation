"""Convert MCP tool results to the agent's phase 6.1 result type."""

from typing import Any

from src.tools.executor import ToolResult


def to_tool_result(name: str, response: Any) -> ToolResult:
    if response.is_error:
        message = "; ".join(block.text for block in response.content
                            if getattr(block, "type", None) == "text")
        return ToolResult(name, False, error=message or "MCP tool failed",
                          error_code="mcp_tool_error")
    data = response.structured_content
    if data is None:
        text = "; ".join(block.text for block in response.content
                         if getattr(block, "type", None) == "text")
        data = {"text": text}
    return ToolResult(name, True, content=data)
