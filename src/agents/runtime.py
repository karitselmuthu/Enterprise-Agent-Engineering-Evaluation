"""Tool enabled incident agent."""
from src.llm.base import Backend
from src.llm.mock_backend import MockBackend
from src.tools.executor import ToolExecutor
from src.tools.mock_infrastructure import infrastructure_registry
from .executor import execute
from .planner import plan
from .state import AgentState

class IncidentAgent:
    def __init__(self, tools: ToolExecutor | None = None, backend: Backend | None = None):
        self.tools = tools or ToolExecutor(
            infrastructure_registry(), frozenset({"get_incident", "get_service_status"}))
        self.backend = backend or MockBackend()

    def run(self, request: str) -> AgentState:
        state = AgentState(request)
        steps = plan(request, self.backend, self.tools.registry)
        state.trace.append({"stage": "selection", "tool": steps[0][0] if steps else None,
                            "arguments": steps[0][1] if steps else {}})
        if not steps:
            state.answer = "No suitable tool selected."
            return state
        execute(state, steps, self.tools)
        result = state.tool_results[-1]
        state.trace.append({"stage": "execution", "tool": result.name, "ok": result.ok,
                            "error_code": result.error_code, "duration_ms": result.duration_ms})
        state.answer = self.backend.interpret(request, result)
        state.trace.append({"stage": "interpretation", "answer": state.answer})
        return state
