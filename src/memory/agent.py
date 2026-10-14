"""Stateful wrapper around the incident agent."""

from pathlib import Path

from src.agents.runtime import IncidentAgent
from src.agents.state import AgentState
from src.mcp.client import MCPIncidentAgent
from .long_term import LongTermMemory
from .persistence import SQLitePersistence
from .short_term import ShortTermMemory


class StatefulIncidentAgent:
    def __init__(self, db_path: str | Path, agent: IncidentAgent | None = None):
        self.long_term = LongTermMemory(SQLitePersistence(db_path))
        self.agent = agent or IncidentAgent()
        self.sessions: dict[str, ShortTermMemory] = {}

    def resume(self, session_id: str) -> ShortTermMemory:
        prior = self.long_term.get_investigation(session_id)
        if prior is None:
            raise KeyError(f"Unknown investigation: {session_id}")
        memory = ShortTermMemory(session_id, current_task=prior["request"])
        for message in self.long_term.conversation(session_id):
            memory.add_message(message["role"], message["content"])
        memory.recent_tool_results = self.long_term.recent_tool_results(session_id)
        self.sessions[session_id] = memory
        return memory

    def _prepare(self, session_id: str, request: str) -> tuple[ShortTermMemory, str]:
        memory = self.sessions.get(session_id)
        if memory is None:
            prior = self.long_term.get_investigation(session_id)
            memory = self.resume(session_id) if prior else ShortTermMemory(session_id)
            self.sessions[session_id] = memory
        # A follow-up without an ID uses the prior task to recover the incident.
        effective_request = request
        if "INC-" not in request.upper() and memory.current_task:
            effective_request = f"{request} ({memory.current_task})"
        return memory, effective_request

    def _record(self, session_id: str, request: str, effective_request: str,
                memory: ShortTermMemory, state: AgentState) -> AgentState:
        memory.current_task = effective_request
        memory.add_message("user", request)
        for result in state.tool_results:
            memory.add_tool_result(result.name, result.ok, result.content if result.ok else result.error)
        approved = [item for item in self.long_term.list_memory(session_id, approved_only=True)
                    if item["kind"] == "fact"]
        if approved:
            state.answer += " Approved context: " + "; ".join(item["content"] for item in approved)
        memory.add_message("assistant", state.answer)
        self.long_term.save_investigation(
            session_id, effective_request, state.answer, user_message=request,
            tool_results=memory.recent_tool_results[-len(state.tool_results):]
            if state.tool_results else [],
        )
        return state

    def investigate(self, session_id: str, request: str) -> AgentState:
        memory, effective_request = self._prepare(session_id, request)
        state = self.agent.run(effective_request)
        return self._record(session_id, request, effective_request, memory, state)


class StatefulMCPIncidentAgent(StatefulIncidentAgent):
    def __init__(self, db_path: str | Path, agent: MCPIncidentAgent):
        super().__init__(db_path)
        self.mcp_agent = agent

    async def investigate(self, session_id: str, request: str) -> AgentState:
        memory, effective_request = self._prepare(session_id, request)
        state = await self.mcp_agent.run(effective_request)
        return self._record(session_id, request, effective_request, memory, state)
