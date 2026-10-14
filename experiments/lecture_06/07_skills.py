"""Discover and run reusable IT operations skills."""
import asyncio

from src.mcp.server import mcp
from src.skills.executor import SkillRunner
from src.skills.loader import load_skills

async def main() -> None:
    registry = load_skills()
    runner = SkillRunner(registry, mcp)
    print(registry.list_skills())
    print(await runner.run("incident_analysis", {"incident_id": "INC-001"}))
    print(await runner.run("service_health", {"service": "api"}))

if __name__ == "__main__":
    asyncio.run(main())
