"""Investigate an incident with MCP tools, SQLite memory, and runbooks."""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp
from src.retrieval.agent import RetrievalIncidentAgent

async def main() -> None:
    with TemporaryDirectory() as directory:
        agent = RetrievalIncidentAgent(Path(directory) / "memory.sqlite3",
                                       MCPIncidentAgent(mcp))
        state = await agent.investigate("demo", "Investigate INC-001")
        print(state.answer)
        print([event for event in state.trace if event["stage"] == "retrieval"])

if __name__ == "__main__":
    asyncio.run(main())
