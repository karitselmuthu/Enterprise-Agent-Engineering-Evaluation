"""Public blueprint generation and agent tool-contract integration."""

import json
import tempfile
import unittest
from pathlib import Path

from simulation.generators import DEFAULT_BLUEPRINTS, build_synthetic_records
from simulation.scenario_loader import load_blueprint, load_scenarios
from simulation.state_manager import SimulationStateManager
from src.agents.simulation_agent import SimulationInvestigator


class SyntheticBlueprintTests(unittest.TestCase):
    def test_five_blueprints_match_committed_public_data(self):
        records = build_synthetic_records()
        committed = [json.loads(line) for line in
                     Path("data/synthetic/scenarios.jsonl").read_text().splitlines()]
        self.assertEqual(records, committed)
        self.assertEqual(len(records), 5)
        scenarios = load_scenarios("data/synthetic/scenarios.jsonl")
        self.assertEqual(set(scenarios), {f"SYN-{n:03d}" for n in range(1, 6)})

    def test_agent_uses_standard_tools_at_different_virtual_minutes(self):
        manager = SimulationStateManager(load_scenarios("data/synthetic/scenarios.jsonl"))
        manager.seek("SYN-002", 5)
        early = SimulationInvestigator(manager.tools("SYN-002")).run("SYN-002")
        self.assertEqual([item.name for item in early.tool_results],
                         ["get_incident_record", "get_server_metrics", "get_application_logs"])
        self.assertTrue(all(item.ok for item in early.tool_results))
        self.assertNotIn("Workers saturated", early.answer)
        manager.seek("SYN-002", 15)
        late = SimulationInvestigator(manager.tools("SYN-002")).run("SYN-002")
        self.assertIn("CPU remained above 90%", late.answer)
        self.assertIn("Checkout requests timing out", late.answer)
        self.assertEqual(len(early.tool_results[1].content["samples"]), 2)
        self.assertEqual(len(late.tool_results[1].content["samples"]), 4)
        self.assertEqual(manager.minute("SYN-001"), 0)

    def test_snapshot_is_frozen_and_permission_cannot_be_escalated(self):
        scenarios = load_scenarios()
        manager = SimulationStateManager({"SIM-016": scenarios["SIM-016"]})
        manager.seek("SIM-016", 5)
        tools = manager.tools("SIM-016", frozenset({"get_server_metrics"}))
        result = tools.execute("get_server_metrics", {"server_id": "prod-app-016"})
        self.assertEqual(result.error_code, "permission_denied")
        frozen = manager.snapshot("SIM-016")
        manager.seek("SIM-016", 10)
        self.assertEqual(frozen.clock.minute, 5)
        self.assertEqual(len(frozen.metrics("prod-app-016")["samples"]), 2)
        with self.assertRaises(ValueError):
            manager.seek("SIM-016", -1)
        self.assertEqual(manager.minute("SIM-016"), 10)

    def test_blueprints_reject_private_labels_and_invalid_metrics(self):
        blueprint = load_blueprint(DEFAULT_BLUEPRINTS / "cpu_saturation.yaml")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.yaml"
            path.write_text(json.dumps({**blueprint, "root_cause": "hidden"}))
            with self.assertRaisesRegex(ValueError, "private labels"):
                load_blueprint(path)
            del blueprint["timeline"][0]["metrics"]["cpu_percent"]
            path.write_text(json.dumps(blueprint))
            with self.assertRaisesRegex(ValueError, "Metrics need"):
                build_synthetic_records(Path(directory))


if __name__ == "__main__":
    unittest.main()
