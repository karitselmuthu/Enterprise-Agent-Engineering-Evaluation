"""Show a bounded prompt after a long investigation history."""
import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from src.context.agent import ContextAwareIncidentAgent
from src.context.manager import ContextManager
from src.context.token_budget import ContextBudget
from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp

async def main() -> None:
    with TemporaryDirectory() as directory:
        agent = ContextAwareIncidentAgent(
            Path(directory) / "memory.sqlite3", MCPIncidentAgent(mcp),
            ContextManager(ContextBudget(320, 80, 20)))
        await agent.investigate("demo", "Investigate INC-001")
        agent.long_term.add_memory("demo", "fact", "Pool utilization reached 95%",
                                   approved=True)
        for number in range(20):
            agent.long_term.save_investigation(
                "demo", "Investigate INC-001", "Previous analysis " + "detail " * 20,
                user_message=f"Earlier follow-up {number} " + "detail " * 20)
        state = await agent.investigate("demo", "Continue investigation")
        print(state.trace[0])
        print(state.answer)

if __name__ == "__main__":
    asyncio.run(main())
