"""Tool declarations with a minimal JSON schema validator."""
from dataclasses import dataclass
from typing import Any, Callable

@dataclass(frozen=True)
class Tool:
    name: str
    description: str
    input_schema: dict[str, Any]
    handler: Callable[..., Any]

    def validate(self, args: dict[str, Any]) -> None:
        if not isinstance(args, dict):
            raise ValueError("Tool arguments must be an object")
        props = self.input_schema["properties"]
        missing = set(self.input_schema.get("required", [])) - args.keys()
        unknown = args.keys() - props.keys()
        if missing or unknown:
            raise ValueError(f"Missing: {sorted(missing)}; unknown: {sorted(unknown)}")
        types = {"string": str, "integer": int, "boolean": bool}
        for key, value in args.items():
            expected = props[key]["type"]
            if not isinstance(value, types[expected]) or expected == "integer" and isinstance(value, bool):
                raise ValueError(f"{key} must be {expected}")

class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"Duplicate tool: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool:
        return self._tools[name]

    def list_tools(self) -> list[dict[str, Any]]:
        return [{"name": t.name, "description": t.description, "inputSchema": t.input_schema}
                for t in self._tools.values()]
