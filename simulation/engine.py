"""Replay one scenario and expose only time-bounded observations."""

from copy import deepcopy

from .clock import VirtualClock
from .scenario_loader import Scenario


class ReplayEngine:
    def __init__(self, scenario: Scenario, clock: VirtualClock | None = None):
        self.scenario = scenario
        self.clock = clock or VirtualClock()

    def visible_events(self) -> tuple[dict, ...]:
        return tuple(event for event in self.scenario.events
                     if event["minute"] <= self.clock.minute)

    def incident(self, incident_id: str) -> dict:
        if incident_id != self.scenario.scenario_id:
            raise KeyError(f"Unknown incident: {incident_id}")
        latest = self.visible_events()[-1]
        return deepcopy({**self.scenario.incident, "status": latest["status"],
                         "observed_minute": self.clock.minute})

    def metrics(self, server_id: str) -> dict:
        if server_id != self.scenario.incident["server_id"]:
            raise KeyError(f"Unknown server: {server_id}")
        self._check_fault("get_server_metrics")
        samples = [{"minute": event["minute"], **event["metrics"]}
                   for event in self.visible_events() if event["metrics"] is not None]
        return deepcopy({"server_id": server_id, "observed_minute": self.clock.minute,
                         "status": "available" if samples else "missing", "samples": samples})

    def logs(self, service: str) -> dict:
        if service != self.scenario.incident["service"]:
            raise KeyError(f"Unknown service: {service}")
        self._check_fault("get_application_logs")
        entries = [{"minute": event["minute"], "service": service,
                    "server_id": self.scenario.incident["server_id"], **log}
                   for event in self.visible_events() for log in event["logs"]]
        return deepcopy({"service": service, "observed_minute": self.clock.minute,
                         "entries": entries})

    def _check_fault(self, tool: str) -> None:
        latest = self.visible_events()[-1]
        if tool in latest.get("faults", []):
            raise TimeoutError(f"Simulated {tool} timeout at minute {self.clock.minute}")
