"""Investigate the optional local Compose service through shared tool contracts."""

import argparse
import json

from simulation.live_stack.backend import live_tools
from src.agents.simulation_agent import SimulationInvestigator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    state = SimulationInvestigator(live_tools(args.url)).run("LIVE-001")
    print(json.dumps({"answer": state.answer,
                      "tools": [{"name": result.name, "ok": result.ok,
                                 "error_code": result.error_code}
                                for result in state.tool_results]}, indent=2))
    return 0 if all(result.ok for result in state.tool_results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
