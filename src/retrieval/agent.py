"""MCP and memory agent enriched with cited runbook sections."""

from pathlib import Path

from src.memory.agent import StatefulMCPIncidentAgent
from src.mcp.client import MCPIncidentAgent
from .retriever import RunbookRetriever


class RetrievalIncidentAgent(StatefulMCPIncidentAgent):
    def __init__(self, db_path: str | Path, mcp_agent: MCPIncidentAgent,
                 retriever: RunbookRetriever | None = None):
        super().__init__(db_path, mcp_agent)
        self.retriever = retriever or RunbookRetriever()

    async def investigate(self, session_id: str, request: str):
        memory, effective_request = self._prepare(session_id, request)
        state = await self.mcp_agent.run(effective_request)
        if state.tool_results and state.tool_results[-1].ok:
            data = state.tool_results[-1].content
            query = " ".join([effective_request] + [str(value) for value in data.values()])
            hits = self.retriever.search(query, limit=2)
            state.trace.append({"stage": "retrieval", "hits": [
                {"path": hit.section.path, "heading": hit.section.heading,
                 "score": round(hit.score, 4)} for hit in hits]})
            if hits:
                guidance = " ".join(
                    f"[{Path(hit.section.path).name} / {hit.section.heading}] "
                    f"{hit.section.text}" for hit in hits)
                state.answer += " Runbook guidance: " + guidance
        return self._record(session_id, request, effective_request, memory, state)
