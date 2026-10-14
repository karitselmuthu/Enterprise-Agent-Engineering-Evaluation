"""Run the MCP agent against a real stdio server subprocess."""
import asyncio
import sys
from pathlib import Path
from mcp.client.stdio import StdioServerParameters
from src.mcp.client import MCPIncidentAgent

async def main() -> None:
    root = Path(__file__).resolve().parents[2]
    server = StdioServerParameters(
        command=sys.executable, args=["-m", "src.mcp.server"], cwd=root)
    state = await MCPIncidentAgent(server).run("Investigate INC-001")
    print(state.answer)
    print(state.trace)

if __name__ == "__main__":
    asyncio.run(main())
