"""Independent virtual clocks and frozen public snapshots for each scenario."""

from copy import deepcopy
from dataclasses import replace
from threading import RLock

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import Scenario
from src.tools.executor import ToolExecutor


class SimulationStateManager:
    def __init__(self, scenarios: dict[str, Scenario]):
        if not scenarios or any(key != scenario.scenario_id
                                for key, scenario in scenarios.items()):
            raise ValueError("Scenarios must have matching unique IDs")
        self._scenarios = dict(scenarios)
        self._minutes = {key: 0 for key in scenarios}
        self._lock = RLock()

    def minute(self, scenario_id: str) -> int:
        with self._lock:
            return self._minutes[scenario_id]

    def seek(self, scenario_id: str, minute: int) -> None:
        VirtualClock(minute)  # Validate before changing shared state.
        with self._lock:
            self._minutes[scenario_id] = minute

    def advance(self, scenario_id: str, minutes: int) -> None:
        with self._lock:
            clock = VirtualClock(self._minutes[scenario_id])
            clock.advance(minutes)
            self._minutes[scenario_id] = clock.minute

    def snapshot(self, scenario_id: str) -> ReplayEngine:
        with self._lock:
            minute = self._minutes[scenario_id]
            scenario = self._scenarios[scenario_id]
            visible = tuple(deepcopy(event) for event in scenario.events
                            if event["minute"] <= minute)
            return ReplayEngine(replace(scenario, incident=deepcopy(scenario.incident),
                                        events=visible), VirtualClock(minute))

    def tools(self, scenario_id: str, allowed: frozenset[str] | None = None) -> ToolExecutor:
        return replay_tools(self.snapshot(scenario_id), allowed)
