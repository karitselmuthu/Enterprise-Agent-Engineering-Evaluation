"""Publish public scenario events on a wall-clock schedule for live polling."""

import asyncio
from dataclasses import dataclass, replace
from time import monotonic

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import Scenario
from src.agents.simulation_agent import SimulationInvestigator
from src.agents.state import AgentState


@dataclass(frozen=True)
class LivePoll:
    minute: int
    observed_at: str
    state: AgentState


class LiveSimulation:
    """Pace a fixed scenario; hand each investigation an immutable time slice."""

    def __init__(self, scenario: Scenario, interval_seconds: float = 1.0):
        if not isinstance(interval_seconds, (int, float)) or isinstance(interval_seconds, bool) \
                or not 0 < interval_seconds < float("inf"):
            raise ValueError("interval_seconds must be a finite positive number")
        self.scenario = scenario
        self.interval_seconds = float(interval_seconds)
        self._published = 0
        self._condition = asyncio.Condition()
        self._task: asyncio.Task | None = None
        self.finished = False

    @property
    def minute(self) -> int:
        if self._published == 0:
            raise RuntimeError("live simulation has not started")
        return self.scenario.events[self._published - 1]["minute"]

    @property
    def published_minutes(self) -> tuple[int, ...]:
        return tuple(event["minute"] for event in self.scenario.events[:self._published])

    async def __aenter__(self) -> "LiveSimulation":
        await self.start()
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.stop()

    async def start(self) -> None:
        if self._task is not None:
            raise RuntimeError("live simulation already started")
        self._published = 1  # The initial event is visible immediately.
        self._task = asyncio.create_task(self._publish())

    async def stop(self) -> None:
        if self._task is None:
            return
        if not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        async with self._condition:
            self.finished = True
            self._condition.notify_all()

    async def wait_for_change(self, after_minute: int) -> int | None:
        """Wait until a newer event is published; return None once stopped."""
        if self._task is None:
            raise RuntimeError("live simulation has not started")
        async with self._condition:
            await self._condition.wait_for(lambda: self.minute > after_minute or self.finished)
            return self.minute if self.minute > after_minute else None

    def snapshot(self) -> ReplayEngine:
        if self._task is None:
            raise RuntimeError("live simulation has not started")
        # The tool handler never receives the future public events or private labels.
        visible = replace(self.scenario, events=self.scenario.events[:self._published])
        return ReplayEngine(visible, VirtualClock(self.minute))

    async def poll(self) -> LivePoll:
        engine = self.snapshot()  # No await between reading the minute and event slice.
        state = await asyncio.to_thread(
            SimulationInvestigator(replay_tools(engine)).run, self.scenario.scenario_id)
        return LivePoll(engine.clock.minute, engine.observed_at(), state)

    async def _publish(self) -> None:
        started = monotonic()
        try:
            for index in range(1, len(self.scenario.events)):
                delay = started + index * self.interval_seconds - monotonic()
                if delay > 0:
                    await asyncio.sleep(delay)
                async with self._condition:
                    self._published = index + 1
                    self._condition.notify_all()
        finally:
            async with self._condition:
                self.finished = True
                self._condition.notify_all()
