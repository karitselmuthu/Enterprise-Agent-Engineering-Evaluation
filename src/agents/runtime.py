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
        self.tools = tools or ToolExecutor(infrastructure_registry(), frozenset({"get_incident"}))
        self.backend = backend or MockBackend()

    def run(self, incident_id: str) -> AgentState:
        state = execute(AgentState(incident_id), plan(incident_id), self.tools)
        result = state.tool_results[-1]
        state.answer = self.backend.generate(result.content) if result.ok else f"Investigation failed: {result.error}"
        return state
