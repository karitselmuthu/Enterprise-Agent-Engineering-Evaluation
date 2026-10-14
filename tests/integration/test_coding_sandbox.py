"""Set RUN_DOCKER_INTEGRATION=1 only on a host with Docker and the image."""
import os
import unittest

from src.coding_agents.code_agent import LogAnalysisCodeAgent


@unittest.skipUnless(os.getenv("RUN_DOCKER_INTEGRATION") == "1",
                     "Docker integration test is opt-in")
class DockerIntegrationTests(unittest.TestCase):
    def test_generated_script_runs_and_passes_fixture_in_container(self):
        report = LogAnalysisCodeAgent().run(
            "Analyze application logs", "ERROR failed\nWARN slow\nINFO ready\n")
        self.assertTrue(report.ok, report.error)
        self.assertTrue(report.tests_passed)
        self.assertEqual(report.sample_result, {"ERROR": 1, "WARN": 1, "INFO": 1})
