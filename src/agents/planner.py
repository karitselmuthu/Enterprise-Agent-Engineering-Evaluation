"""Ask the configured backend to select a tool."""
from src.llm.base import Backend
from src.tools.registry import ToolRegistry

def plan(request: str, backend: Backend,
         registry: ToolRegistry) -> list[tuple[str, dict]]:
    if not request.strip():
        raise ValueError("request is required")
    choice = backend.select_tool(request, registry.list_tools())
    return [choice] if choice else []
