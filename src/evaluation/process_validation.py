"""Process checks for bounded, cited investigations across repeated runs.

The completion check is a deterministic workflow proxy, not semantic RCA accuracy.
"""

import re
from statistics import mean

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import DEFAULT_SCENARIOS, load_scenarios
from src.agents.simulation_agent import SimulationInvestigator

from .simulation_eval import DEFAULT_TRUTH, load_ground_truth


REQUIRED_PHASES = ("observe", "policy_check", "execute_read_action",
                   "normalize_evidence", "verify", "final_diagnosis", "completed")


def inspect_process(state) -> dict:
    record = state.investigation
    phases = [event["phase"] for event in record.events if event["kind"] == "phase_entered"]
    cards = {card.evidence_id: card for card in state.evidence_cards}
    cited = set(re.findall(r"\[(ev-\d+)\]", state.answer))
    references_resolve = all(
        card.raw_reference.startswith(f"tool-result://{record.investigation_id}/")
        and card.raw_reference.rsplit("/", 1)[-1].isdigit()
        and 1 <= int(card.raw_reference.rsplit("/", 1)[-1]) <= len(state.tool_results)
        and state.tool_results[int(card.raw_reference.rsplit("/", 1)[-1]) - 1].name == card.source
        and state.tool_results[int(card.raw_reference.rsplit("/", 1)[-1]) - 1].ok
        for card in cards.values())
    observation_cards = {identifier for identifier, card in cards.items()
                         if card.source_type != "incident"}
    first = {phase: phases.index(phase) for phase in REQUIRED_PHASES if phase in phases}
    trajectory_valid = (record.phase == "completed" and
                        all(phase in first for phase in REQUIRED_PHASES) and
                        all(first[left] < first[right] for left, right in zip(
                            REQUIRED_PHASES, REQUIRED_PHASES[1:])) and
                        [event["sequence_number"] for event in record.events]
                        == list(range(1, len(record.events) + 1)) and
                        record.tool_calls <= record.budget.max_tool_calls)
    citation_integrity = references_resolve and observation_cards <= cited <= cards.keys()
    return {"trajectory_valid": trajectory_valid,
            "citation_integrity": citation_integrity,
            "evidence_card_count": len(cards), "cited_card_count": len(cited),
            "tool_calls_within_budget": record.tool_calls <= record.budget.max_tool_calls}


def evaluate_repeatability(trials: int = 5, public_path=DEFAULT_SCENARIOS,
                           truth_path=DEFAULT_TRUTH) -> dict:
    if isinstance(trials, bool) or not isinstance(trials, int) or trials < 1:
        raise ValueError("trials must be a positive integer")
    scenarios = load_scenarios(public_path)
    labels = load_ground_truth(truth_path)
    if set(scenarios) != set(labels):
        raise ValueError("Scenario and label IDs differ")
    results = []
    for identifier in sorted(scenarios):
        attempts = []
        for _ in range(trials):
            engine = ReplayEngine(scenarios[identifier],
                                  VirtualClock(labels[identifier]["evaluation_minute"]))
            state = SimulationInvestigator(replay_tools(engine)).run(identifier)
            checks = inspect_process(state)
            selected = {result.name for result in state.tool_results}
            checks["required_tools_selected"] = set(labels[identifier]["expected_tools"]) <= selected
            checks["workflow_proxy_pass"] = all((checks["trajectory_valid"],
                                                  checks["citation_integrity"],
                                                  checks["required_tools_selected"]))
            attempts.append(checks)
        results.append({"scenario_id": identifier, "attempts": attempts,
                        "pass_at_1_proxy": attempts[0]["workflow_proxy_pass"],
                        "all_success_proxy": all(item["workflow_proxy_pass"] for item in attempts)})
    return {"scenario_count": len(results), "trials": trials,
            "pass_at_1_proxy_rate": mean(item["pass_at_1_proxy"] for item in results),
            "all_success_proxy_rate": mean(item["all_success_proxy"] for item in results),
            "results": results,
            "scope": "Deterministic workflow, required tool names, and citation references only; "
                     "does not score semantic diagnosis or remediation quality"}
