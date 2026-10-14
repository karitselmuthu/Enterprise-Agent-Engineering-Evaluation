import unittest
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from src.coding_agents.code_agent import (
    LogAnalysisCodeAgent, OllamaCodeGenerator, TemplateLogGenerator)
from src.coding_agents.sandbox import DockerSandbox, SandboxResult, SandboxUnavailable
from src.coding_agents.validator import CodeValidationError, validate_python


class CodingAgentTests(unittest.TestCase):
    def test_generated_code_passes_static_validation(self):
        source = TemplateLogGenerator().generate("Analyze application logs")
        validate_python(source)
        self.assertIn("def analyze", source)

    def test_local_model_source_is_still_validated(self):
        import json
        payload = {"message": {"content": "```python\nimport os\n```"}}
        with patch("src.coding_agents.code_agent.urlopen",
                   return_value=BytesIO(json.dumps(payload).encode())):
            generator = OllamaCodeGenerator("local-model")
            source = generator.generate("Analyze logs")
        with self.assertRaises(CodeValidationError):
            validate_python(source)

    def test_static_validation_rejects_unsafe_code_and_syntax(self):
        for source in ("import os\n", "from sys import argv\n",
                       "eval('1')\n", "def broken(:\n"):
            with self.subTest(source=source):
                with self.assertRaises(CodeValidationError):
                    validate_python(source)

    def test_docker_command_enforces_isolation(self):
        command = DockerSandbox().build_command(Path("/tmp/analyze.py"), "unique-name")
        for flag in ("--network", "--read-only", "--cap-drop", "--memory",
                     "--memory-swap", "--cpus", "--pids-limit", "--pull",
                     "--user", "--mount", "--security-opt"):
            self.assertIn(flag, command)
        self.assertEqual(command[command.index("--network") + 1], "none")
        self.assertEqual(command[command.index("--pull") + 1], "never")
        self.assertIn("readonly", command[command.index("--mount") + 1])

    def test_agent_runs_sample_and_test_in_sandbox(self):
        class FakeSandbox:
            def __init__(self):
                self.inputs = []
            def run(self, source, input_text):
                self.inputs.append(input_text)
                counts = {level: sum(level in line for line in input_text.splitlines())
                          for level in ("ERROR", "WARN", "INFO")}
                import json
                return SandboxResult(json.dumps(counts), "", 0)
        sandbox = FakeSandbox()
        report = LogAnalysisCodeAgent(sandbox=sandbox).run(
            "Analyze application logs", "ERROR fail\nINFO ready\n")
        self.assertTrue(report.ok)
        self.assertTrue(report.tests_passed)
        self.assertEqual(report.sample_result["ERROR"], 1)
        self.assertEqual(len(sandbox.inputs), 2)

    def test_agent_reports_sandbox_failure_without_host_fallback(self):
        class MissingSandbox:
            def run(self, source, input_text):
                raise SandboxUnavailable("Docker unavailable")
        report = LogAnalysisCodeAgent(sandbox=MissingSandbox()).run(
            "Analyze application logs", "ERROR fail\n")
        self.assertFalse(report.ok)
        self.assertIn("Docker unavailable", report.error)
