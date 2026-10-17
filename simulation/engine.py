"""Replay one scenario and expose only time-bounded observations."""

from copy import deepcopy
from datetime import datetime, timedelta

from .clock import VirtualClock
from .scenario_loader import Scenario


class ReplayEngine:
    def __init__(self, scenario: Scenario, clock: VirtualClock | None = None):
        self.scenario = scenario
        self.clock = clock or VirtualClock()

    def visible_events(self) -> tuple[dict, ...]:
        return tuple(event for event in self.scenario.events
                     if event["minute"] <= self.clock.minute)

    def observed_at(self) -> str:
        start = datetime.fromisoformat(self.scenario.events[0]["timestamp"].replace("Z", "+00:00"))
        return (start + timedelta(minutes=self.clock.minute)).isoformat().replace("+00:00", "Z")

    def incident(self, incident_id: str) -> dict:
        primary = self.scenario.incident
        related = next((item for item in primary.get("related_incidents", [])
                        if item["id"] == incident_id), None)
        if incident_id != self.scenario.scenario_id and related is None:
            raise KeyError(f"Unknown incident: {incident_id}")
        if self.clock.minute < self.scenario.incident.get("alert_at_minute", 0):
            raise KeyError(f"Incident not yet raised: {incident_id}")
        latest = self.visible_events()[-1]
        incident = primary if related is None else related
        return deepcopy({**incident, "status": latest["status"],
                         "observed_minute": self.clock.minute,
                         "observed_at": self.observed_at()})

    def metrics(self, server_id: str) -> dict:
        if server_id != self.scenario.incident["server_id"]:
            raise KeyError(f"Unknown server: {server_id}")
        self._check_fault("get_server_metrics")
        samples = [{"minute": event["minute"], **event["metrics"]}
                   for event in self.visible_events() if event["metrics"] is not None]
        return deepcopy({"server_id": server_id, "observed_minute": self.clock.minute,
                         "observed_at": self.observed_at(),
                         "status": "available" if samples else "missing", "samples": samples})

    def database_metrics(self, database_id: str) -> dict:
        if database_id != self.scenario.incident.get("database_id"):
            raise KeyError(f"Unknown database: {database_id}")
        self._check_fault("get_database_metrics")
        samples = [{"minute": event["minute"], **event["database_metrics"]}
                   for event in self.visible_events() if event.get("database_metrics") is not None]
        return deepcopy({"database_id": database_id, "observed_minute": self.clock.minute,
                         "observed_at": self.observed_at(),
                         "status": "available" if samples else "missing", "samples": samples})

    def logs(self, service: str) -> dict:
        services = {self.scenario.incident["service"]} | {
            item["service"] for item in self.scenario.incident.get("related_incidents", [])}
        if service not in services:
            raise KeyError(f"Unknown service: {service}")
        self._check_fault("get_application_logs")
        entries = [{"minute": event["minute"], "service": service,
                    "server_id": self.scenario.incident["server_id"], **log}
                   for event in self.visible_events() for log in event["logs"]
                   if log.get("service", self.scenario.incident["service"]) == service]
        return deepcopy({"service": service, "observed_minute": self.clock.minute,
                         "observed_at": self.observed_at(),
                         "entries": entries})

    def pod_events(self, pod: str) -> dict:
        if pod != self.scenario.incident.get("pod_name"):
            raise KeyError(f"Unknown pod: {pod}")
        entries = [{"minute": event["minute"], **item}
                   for event in self.visible_events()
                   for item in event.get("pod_events", [])]
        return deepcopy({"pod": pod, "observed_minute": self.clock.minute,
                         "observed_at": self.observed_at(), "entries": entries})

    def network_peers(self, service: str) -> dict:
        if service != self.scenario.incident["service"] \
                or not self.scenario.incident.get("network_scope"):
            raise KeyError(f"No peer network metrics for service: {service}")
        samples = [{"minute": event["minute"], **item}
                   for event in self.visible_events()
                   for item in event.get("network_peers", [])]
        return deepcopy({"service": service, "observed_minute": self.clock.minute,
                         "observed_at": self.observed_at(), "samples": samples})

    def _check_fault(self, tool: str) -> None:
        latest = self.visible_events()[-1]
        if tool in latest.get("faults", []):
            raise TimeoutError(f"Simulated {tool} timeout at minute {self.clock.minute}")
