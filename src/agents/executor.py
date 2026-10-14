"""Execute an agent plan."""
from src.tools.executor import ToolExecutor
from .state import AgentState

def execute(state: AgentState, steps: list[tuple[str, dict[str, str]]],
            tools: ToolExecutor) -> AgentState:
    for name, arguments in steps:
        result = tools.execute(name, arguments)
        state.tool_results.append(result)
        if not result.ok:
            break
    return state
