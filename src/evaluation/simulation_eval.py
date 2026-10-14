"""Read private labels only on the evaluation side of replay."""

import json
from pathlib import Path
from statistics import mean

from src.agents.simulation_agent import SimulationInvestigator
from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import DEFAULT_SCENARIOS, load_scenarios


DEFAULT_TRUTH = Path(__file__).resolve().parents[2] / "data/evaluation_datasets/simulation_ground_truth.jsonl"


def load_ground_truth(path: str | Path = DEFAULT_TRUTH) -> dict[str, dict]:
    labels: dict[str, dict] = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            item = json.loads(line)
            identifier = item["scenario_id"]
            if (not isinstance(identifier, str) or not identifier or identifier in labels
                    or not isinstance(item["root_cause"], str)
                    or not isinstance(item["expected_tools"], list)
                    or not all(isinstance(tool, str) and tool for tool in item["expected_tools"])
                    or not isinstance(item["evaluation_minute"], int)
                    or item["evaluation_minute"] < 0):
                raise ValueError("invalid or duplicate label")
            labels[identifier] = item
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid ground truth line {number}: {exc}") from exc
    if not labels:
        raise ValueError("No ground truth labels found")
    return labels


def run_simulation_evaluation(public_path: str | Path = DEFAULT_SCENARIOS,
                              truth_path: str | Path = DEFAULT_TRUTH) -> dict:
    scenarios = load_scenarios(public_path)
    truth = load_ground_truth(truth_path)
    if set(scenarios) != set(truth):
        raise ValueError("Public scenario and ground-truth IDs differ")
    results = []
    for identifier in sorted(scenarios):
        label = truth[identifier]
        engine = ReplayEngine(scenarios[identifier], VirtualClock(label["evaluation_minute"]))
        # The investigator receives only a standard ToolExecutor, not labels.
        state = SimulationInvestigator(replay_tools(engine)).run(identifier)
        selected = [event["tool"] for event in state.trace
                    if event.get("stage") == "selection" and event.get("tool")]
        expected = set(label["expected_tools"])
        results.append({
            "scenario_id": identifier,
            "selected_tools": selected,
            "tool_coverage": len(expected.intersection(selected)) / len(expected) if expected else 1.0,
            "tool_execution_success": (sum(result.ok for result in state.tool_results)
                                       / len(state.tool_results) if state.tool_results else 0.0),
            "literal_root_cause_phrase_found": label["root_cause"].casefold() in state.answer.casefold(),
            "answer": state.answer,
        })
    return {
        "scenario_count": len(results),
        "mean_tool_coverage": mean(item["tool_coverage"] for item in results),
        "mean_tool_execution_success": mean(item["tool_execution_success"] for item in results),
        "literal_root_cause_phrase_rate": mean(
            float(item["literal_root_cause_phrase_found"]) for item in results),
        "results": results,
    }
