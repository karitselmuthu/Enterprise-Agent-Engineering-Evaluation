"""Investigate a generated scenario through the standard agent tool executor."""

import argparse
import json
from pathlib import Path

from simulation.scenario_loader import load_scenarios
from simulation.state_manager import SimulationStateManager
from src.agents.simulation_agent import SimulationInvestigator


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario_id", help="For example SYN-002")
    parser.add_argument("--minute", type=int, default=10)
    parser.add_argument("--data", type=Path, default=Path("data/synthetic/scenarios.jsonl"))
    args = parser.parse_args()
    manager = SimulationStateManager(load_scenarios(args.data))
    manager.seek(args.scenario_id, args.minute)
    state = SimulationInvestigator(manager.tools(args.scenario_id)).run(args.scenario_id)
    print(json.dumps({"scenario_id": args.scenario_id, "minute": args.minute,
                      "answer": state.answer,
                      "tool_results": [{"name": item.name, "ok": item.ok,
                                        "error_code": item.error_code,
                                        "content": item.content} for item in state.tool_results]},
                     indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
