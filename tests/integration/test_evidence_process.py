"""Replay investigations expose traceable observations and bounded process checks."""

import unittest
from dataclasses import replace

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import load_scenarios
from src.agents.investigation import InvestigationBudget
from src.agents.simulation_agent import SimulationInvestigator
from src.evaluation.process_validation import evaluate_repeatability, inspect_process


class EvidenceProcessTests(unittest.TestCase):
    def test_cards_reference_observed_tool_results(self):
        scenario = load_scenarios()["SIM-004"]
        state = SimulationInvestigator(replay_tools(
            ReplayEngine(scenario, VirtualClock(25)))).run("SIM-004")
        self.assertTrue(inspect_process(state)["citation_integrity"])
        self.assertTrue(inspect_process(state)["trajectory_valid"])
        self.assertTrue(any(card.source_type == "log" for card in state.evidence_cards))
        self.assertTrue(all("root_cause" not in card.observation
                            for card in state.evidence_cards))
        state.answer += " [ev-9999]"
        self.assertFalse(inspect_process(state)["citation_integrity"])
        state.answer = state.answer.replace(" [ev-9999]", "")
        state.evidence_cards[1] = replace(state.evidence_cards[1],
                                          raw_reference="tool-result://wrong/2")
        self.assertFalse(inspect_process(state)["citation_integrity"])

    def test_tool_budget_stops_additional_execution(self):
        scenario = load_scenarios()["SIM-001"]
        tools = replay_tools(ReplayEngine(scenario, VirtualClock(10)))
        state = SimulationInvestigator(tools, InvestigationBudget(max_tool_calls=1)).run("SIM-001")
        self.assertEqual(state.investigation.tool_calls, 1)
        self.assertEqual([result.error_code for result in state.tool_results[1:]],
                         ["budget_exceeded", "budget_exceeded"])
        self.assertIn("unavailable", state.answer)

    def test_denied_tool_is_not_executed(self):
        scenario = load_scenarios()["SIM-016"]
        state = SimulationInvestigator(replay_tools(
            ReplayEngine(scenario, VirtualClock(10)))).run("SIM-016")
        events = state.investigation.events
        denied = [event for event in events if event["kind"] == "policy_checked"
                  and event["tool"] == "get_server_metrics"]
        self.assertEqual(len(denied), 1)
        self.assertFalse(denied[0]["allowed"])
        self.assertFalse(any(event["kind"] == "tool_completed"
                             and event["tool"] == "get_server_metrics" for event in events))

    def test_repeated_run_process_proxy_is_explicit(self):
        report = evaluate_repeatability(trials=3)
        self.assertEqual(report["scenario_count"], 25)
        self.assertEqual(report["trials"], 3)
        self.assertEqual(report["all_success_proxy_rate"], 1)
        self.assertIn("does not score semantic diagnosis", report["scope"])
