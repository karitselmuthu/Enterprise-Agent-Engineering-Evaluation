"""Discover and call permitted MCP tools, then interpret their results."""

from typing import Any

from mcp import Client

from src.agents.state import AgentState
from src.llm.base import Backend
from src.llm.mock_backend import MockBackend
from src.tools.executor import ToolResult
from .adapters import to_tool_result


class MCPIncidentAgent:
    def __init__(self, server: Any, allowed: frozenset[str] | None = None,
                 backend: Backend | None = None):
        self.server = server
        self.allowed = (allowed if allowed is not None
                        else frozenset({"incident_record", "service_status"}))
        self.backend = backend or MockBackend()

    async def run(self, request: str) -> AgentState:
        try:
            return await self._run_connected(request)
        except (ConnectionError, OSError, TimeoutError) as exc:
            state = AgentState(request)
            result = ToolResult("mcp_connection", False, error=str(exc),
                                error_code="mcp_unavailable")
            state.tool_results.append(result)
            state.trace.append({"stage": "connection", "ok": False,
                                "error_code": result.error_code})
            state.answer = f"Investigation unavailable: {exc}"
            return state

    async def _run_connected(self, request: str) -> AgentState:
        state = AgentState(request)
        async with Client(self.server) as client:
            listed = await client.list_tools()
            discovered = {tool.name: tool for tool in listed.tools}
            visible = [tool.model_dump(by_alias=True, exclude_none=True)
                       for name, tool in discovered.items() if name in self.allowed]
            state.trace.append({"stage": "discovery", "tools": sorted(discovered)})
            try:
                choice = self.backend.select_tool(request, visible)
            except Exception as exc:
                result = ToolResult("selector", False, error=str(exc),
                                    error_code="selection_failed")
                state.tool_results.append(result)
                state.answer = f"Investigation failed: {exc}"
                state.trace.append({"stage": "selection", "ok": False,
                                    "error_code": result.error_code})
                return state
            if choice is None:
                state.answer = "No suitable tool selected."
                return state
            name, arguments = choice
            state.trace.append({"stage": "selection", "tool": name, "arguments": arguments})
            if name not in discovered:
                result = ToolResult(name, False, error=f"Unknown MCP tool: {name}",
                                    error_code="unknown_tool")
            elif name not in self.allowed:
                result = ToolResult(name, False, error=f"MCP tool not permitted: {name}",
                                    error_code="permission_denied")
            else:
                try:
                    result = to_tool_result(name, await client.call_tool(name, arguments))
                except Exception as exc:
                    result = ToolResult(name, False, error=str(exc), error_code="mcp_call_failed")
            state.tool_results.append(result)
            state.trace.append({"stage": "execution", "tool": name, "ok": result.ok,
                                "error_code": result.error_code})
            try:
                state.answer = self.backend.interpret(request, result)
            except Exception as exc:
                state.answer = f"Interpretation failed: {exc}"
                state.tool_results[-1] = ToolResult(
                    name, False, error=str(exc), error_code="interpretation_failed")
            state.trace.append({"stage": "interpretation", "answer": state.answer})
            return state
