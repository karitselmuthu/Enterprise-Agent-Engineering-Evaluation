import tempfile
import unittest
from pathlib import Path

from src.skills.loader import load_skills
from src.skills.registry import SkillDefinition, SkillRegistry


class SkillDefinitionTests(unittest.TestCase):
    def test_discovery_and_manifest_fields(self):
        registry = load_skills()
        self.assertEqual(registry.list_skills(),
                         ["incident_analysis", "service_health"])
        skill = registry.get("incident_analysis")
        self.assertTrue(skill.purpose)
        self.assertEqual(skill.input_requirements, {"incident_id": "string"})
        self.assertEqual(skill.permitted_tools, ("incident_record",))
        self.assertIn("${incident_id}", skill.execution_instructions)
        self.assertEqual(skill.output_format, "json")
        self.assertEqual(skill.error_handling, "return_error")

    def test_invalid_manifest_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "broken"
            path.mkdir()
            (path / "skill.json").write_text('{"name": "broken"}')
            with self.assertRaises(ValueError):
                load_skills(directory)

    def test_undeclared_instruction_input_is_rejected(self):
        with self.assertRaises(ValueError):
            SkillDefinition("bad", "purpose", {"incident_id": "string"},
                            ("incident_record",), "Investigate ${other}",
                            "json", "return_error")
