"""Context-aware continuation of MCP, memory, and retrieval phases."""

from pathlib import Path

from src.mcp.client import MCPIncidentAgent
from src.retrieval.agent import RetrievalIncidentAgent
from src.retrieval.retriever import RunbookRetriever
from .manager import ContextManager


class ContextAwareIncidentAgent(RetrievalIncidentAgent):
    def __init__(self, db_path: str | Path, mcp_agent: MCPIncidentAgent,
                 context_manager: ContextManager | None = None,
                 retriever: RunbookRetriever | None = None):
        super().__init__(db_path, mcp_agent, retriever)
        self.context_manager = context_manager or ContextManager()

    async def investigate(self, session_id: str, request: str):
        memory, effective_request = self._prepare(session_id, request)
        facts = [item["content"] for item in
                 self.long_term.list_memory(session_id, approved_only=True)
                 if item["kind"] == "fact"]
        managed = self.context_manager.build(
            effective_request, memory.conversation, memory.recent_tool_results, facts)
        state = await self.mcp_agent.run(managed.prompt)
        state.trace.insert(0, {"stage": "context", "estimated_tokens": managed.estimated_tokens,
                               "input_budget": managed.input_budget,
                               "summarized_turns": managed.summarized_turns,
                               "included_tool_results": managed.included_tool_results})
        self._enrich(state, effective_request)
        return self._record(session_id, request, effective_request, memory, state)
