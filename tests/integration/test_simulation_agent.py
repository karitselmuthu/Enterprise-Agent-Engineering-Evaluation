"""Agent-to-tool-to-replay integration without exposing private labels."""

import json
import tempfile
import unittest
from pathlib import Path

from simulation.adapters.tools import TOOL_NAMES, replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import load_scenarios
from src.agents.simulation_agent import SimulationInvestigator
from src.evaluation.simulation_eval import run_simulation_evaluation


class SimulationAgentTests(unittest.TestCase):
    def setUp(self):
        self.scenarios = load_scenarios()

    def test_all_scenarios_execute_with_three_standard_tools(self):
        self.assertEqual(len(TOOL_NAMES), 3)
        for identifier, scenario in self.scenarios.items():
            with self.subTest(identifier=identifier):
                state = SimulationInvestigator(replay_tools(
                    ReplayEngine(scenario, VirtualClock(10)))).run(identifier)
                self.assertEqual(len(state.tool_results), 3)
                self.assertNotIn("root_cause", str(state.trace))
                self.assertNotIn("expected_findings", str(state.tool_results))

    def test_permission_denial_is_reported_without_bypass(self):
        engine = ReplayEngine(self.scenarios["SIM-016"], VirtualClock(10))
        state = SimulationInvestigator(replay_tools(engine)).run("SIM-016")
        self.assertEqual(state.tool_results[1].error_code, "permission_denied")
        self.assertIn("unavailable", state.answer)

    def test_standard_tool_schema_rejects_extra_arguments(self):
        engine = ReplayEngine(self.scenarios["SIM-001"])
        result = replay_tools(engine).execute(
            "get_server_metrics", {"server_id": "prod-app-001", "root_cause": "guess"})
        self.assertFalse(result.ok)
        self.assertEqual(result.error_code, "invalid_arguments")

    def test_timeout_and_missing_data_do_not_invent_cause(self):
        timed = SimulationInvestigator(replay_tools(ReplayEngine(
            self.scenarios["SIM-012"], VirtualClock(10)))).run("SIM-012")
        self.assertFalse(timed.tool_results[1].ok)
        self.assertEqual(timed.tool_results[1].error_code, "timeout")
        self.assertIn("Simulated get_server_metrics timeout", timed.tool_results[1].error)
        self.assertIn("unavailable", timed.answer)
        missing = SimulationInvestigator(replay_tools(ReplayEngine(
            self.scenarios["SIM-011"], VirtualClock(10)))).run("SIM-011")
        self.assertIn("Insufficient evidence", missing.answer)

    def test_healthy_scenario_avoids_inventing_incident(self):
        state = SimulationInvestigator(replay_tools(ReplayEngine(
            self.scenarios["SIM-017"], VirtualClock(10)))).run("SIM-017")
        self.assertIn("No active incident", state.answer)

    def test_evaluator_joins_private_labels_after_agent_run(self):
        report = run_simulation_evaluation()
        self.assertEqual(report["scenario_count"], 20)
        self.assertEqual(report["mean_tool_coverage"], 1)
        self.assertLess(report["mean_tool_execution_success"], 1)

    def test_evaluator_rejects_incomplete_ground_truth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "partial.jsonl"
            path.write_text(json.dumps({"scenario_id": "SIM-001", "root_cause": "x",
                                        "expected_tools": [], "evaluation_minute": 10}) + "\n")
            with self.assertRaisesRegex(ValueError, "IDs differ"):
                run_simulation_evaluation(truth_path=path)
