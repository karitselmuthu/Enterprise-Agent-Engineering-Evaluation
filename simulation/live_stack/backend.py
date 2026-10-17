"""Read the optional live service through the standard observation methods."""

import json
from urllib.parse import urlencode, urlsplit
from urllib.request import urlopen

from simulation.adapters.tools import contract_tools


LIVE_ALLOWED = frozenset({"get_incident_record", "get_server_metrics",
                          "get_application_logs"})


class LiveBackend:
    def __init__(self, base_url: str, timeout_seconds: float = 2.0):
        parsed = urlsplit(base_url)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
                or parsed.port is None or parsed.username or parsed.password
                or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
            raise ValueError("Live demo URL must use local loopback")
        if not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise ValueError("Timeout must be positive")
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def _get(self, route: str, field: str, value: str) -> dict:
        with urlopen(f"{self.base_url}{route}?{urlencode({field: value})}",
                     timeout=self.timeout_seconds) as response:
            result = json.load(response)
        if not isinstance(result, dict):
            raise ValueError("Malformed live observation")
        return result

    def incident(self, incident_id: str) -> dict:
        return self._get("/v1/incident", "incident_id", incident_id)

    def metrics(self, server_id: str) -> dict:
        return self._get("/v1/metrics", "server_id", server_id)

    def logs(self, service: str) -> dict:
        return self._get("/v1/logs", "service", service)

    def pod_events(self, pod: str) -> dict:
        raise KeyError(f"No pod events for {pod}")

    def network_peers(self, service: str) -> dict:
        raise KeyError(f"No peer metrics for {service}")


def live_tools(base_url: str):
    return contract_tools(LiveBackend(base_url), LIVE_ALLOWED)
