"""Opt-in Compose smoke test for the lightweight SQLite fault demo."""

import os
import subprocess
import time
import unittest
from urllib.error import URLError
from urllib.request import urlopen

from simulation.live_stack.backend import live_tools
from src.agents.simulation_agent import SimulationInvestigator


@unittest.skipUnless(os.getenv("RUN_LIVE_COMPOSE") == "1", "Compose smoke test is opt-in")
class LiveComposeTests(unittest.TestCase):
    def test_compose_fault_flow(self):
        command = ["docker", "compose", "-p", "eae-live-ci", "--profile", "live-demo"]
        try:
            subprocess.run(command + ["up", "--build", "-d"], check=True, timeout=180)
            for _ in range(40):
                try:
                    with urlopen("http://127.0.0.1:8765/health", timeout=1):
                        break
                except (URLError, TimeoutError, ConnectionError):
                    time.sleep(0.5)
            else:
                self.fail("Live Compose service did not become healthy")
            state = SimulationInvestigator(live_tools("http://127.0.0.1:8765")).run(
                "LIVE-001")
            self.assertTrue(all(item.ok for item in state.tool_results))
            self.assertIn("No active incident", state.answer)
        except Exception:
            subprocess.run(command + ["ps", "-a"], check=False, timeout=15)
            subprocess.run(command + ["logs", "live-demo"], check=False, timeout=15)
            raise
        finally:
            subprocess.run(command + ["down", "-v"], check=False, timeout=60)


if __name__ == "__main__":
    unittest.main()
