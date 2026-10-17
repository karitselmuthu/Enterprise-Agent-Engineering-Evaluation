"""Optional live backend uses the same agent-facing tools without Docker."""

from http.server import ThreadingHTTPServer
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Thread
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from simulation.live_stack.backend import LiveBackend, live_tools
from simulation.live_stack.service import LiveStore, make_handler
from src.agents.simulation_agent import SimulationInvestigator


class LiveDemoTests(unittest.TestCase):
    def test_fault_and_recovery_flow_through_standard_tools(self):
        with TemporaryDirectory() as directory:
            store = LiveStore(Path(directory) / "live.sqlite3")
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store))
            thread = Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
            try:
                healthy = SimulationInvestigator(live_tools(url)).run("LIVE-001")
                self.assertIn("No active incident", healthy.answer)
                self.assertTrue(all(result.ok for result in healthy.tool_results))
                with self.assertRaises(HTTPError) as error:
                    self._inject(url, "unknown_failure")
                self.assertEqual(error.exception.code, 400)
                error.exception.close()
                self.assertEqual(store.incident("LIVE-001")["status"], "healthy")
                self._inject(url, "database_failure")
                failing = SimulationInvestigator(live_tools(url)).run("LIVE-001")
                self.assertIn("Database connection refused", failing.answer)
                self.assertEqual(failing.tool_results[1].content["observed_minute"], 1)
                self._inject(url, "recovered")
                recovered = SimulationInvestigator(live_tools(url)).run("LIVE-001")
                self.assertIn("Confirm sustained recovery", recovered.answer)
                denied = live_tools(url).execute("get_pod_events", {"pod": "x"})
                self.assertEqual(denied.error_code, "permission_denied")
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)

    @staticmethod
    def _inject(url: str, mode: str):
        request = Request(url + "/control/fault",
                          data=json.dumps({"mode": mode}).encode("utf-8"),
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request, timeout=2) as response:
            return json.load(response)

    def test_live_backend_rejects_nonlocal_url(self):
        with self.assertRaises(ValueError):
            LiveBackend("http://localhost:8765@remote.example")


if __name__ == "__main__":
    unittest.main()
