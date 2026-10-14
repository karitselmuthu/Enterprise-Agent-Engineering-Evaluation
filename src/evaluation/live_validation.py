"""Exercise paced incident publication and concurrent agent polling."""

import asyncio
from time import monotonic

from simulation.live import LiveSimulation, LivePoll
from simulation.scenario_loader import load_scenarios


def _summarize(poll: LivePoll, client: int) -> dict:
    results = poll.state.tool_results
    incident = next((result for result in results
                     if result.name == "get_incident_record"), None)
    return {
        "client": client,
        "minute": poll.minute,
        "observed_at": poll.observed_at,
        "status": incident.content["status"] if incident and incident.ok else "not_raised",
        "tools": [{"name": result.name, "ok": result.ok,
                   "error_code": result.error_code,
                   "observed_minute": result.content.get("observed_minute")
                   if result.ok and isinstance(result.content, dict) else None,
                   "latest_sample_minute": max(
                       (sample["minute"] for sample in result.content.get("samples", [])),
                       default=None) if result.ok and isinstance(result.content, dict) else None,
                   "latest_log_minute": max(
                       (entry["minute"] for entry in result.content.get("entries", [])),
                       default=None) if result.ok and isinstance(result.content, dict) else None}
                  for result in results],
        "answer": poll.state.answer,
    }


async def validate_mode_b(scenario_id: str = "SIM-004", interval_seconds: float = 0.05,
                          poll_interval_seconds: float = 0.01,
                          clients: int = 3) -> dict:
    if not isinstance(clients, int) or isinstance(clients, bool) or clients < 2:
        raise ValueError("clients must be an integer of at least two")
    if (not isinstance(poll_interval_seconds, (int, float))
            or isinstance(poll_interval_seconds, bool)
            or not 0 < poll_interval_seconds < float("inf")):
        raise ValueError("poll_interval_seconds must be a finite positive number")
    scenario = load_scenarios()[scenario_id]
    observations: list[dict] = []
    in_flight = 0
    max_in_flight = 0
    first_poll_barrier = asyncio.Barrier(clients)

    async with LiveSimulation(scenario, interval_seconds) as live:
        started = monotonic()

        async def run_poller(client: int) -> None:
            nonlocal in_flight, max_in_flight
            first_poll = True
            while True:
                in_flight += 1
                max_in_flight = max(max_in_flight, in_flight)
                try:
                    if first_poll:
                        # Launch one synchronized request wave for a reliable
                        # concurrency check even on very fast machines.
                        await first_poll_barrier.wait()
                        first_poll = False
                    observation = _summarize(await live.poll(), client)
                    observations.append(observation)
                finally:
                    in_flight -= 1
                if live.finished and observation["minute"] == scenario.events[-1]["minute"]:
                    break
                await asyncio.sleep(poll_interval_seconds)

        await asyncio.gather(*(run_poller(index) for index in range(clients)))
        elapsed_seconds = monotonic() - started
        published_minutes = live.published_minutes

    by_client = {index: [entry for entry in observations if entry["client"] == index]
                 for index in range(clients)}
    checks = {
        "all_events_published": published_minutes == tuple(event["minute"]
                                                           for event in scenario.events),
        "multiple_clients_polled": all(len(entries) >= 2 for entries in by_client.values()),
        "polls_overlapped": max_in_flight >= 2,
        "client_minutes_monotonic": all(
            [entry["minute"] for entry in entries] ==
            sorted(entry["minute"] for entry in entries)
            for entries in by_client.values()),
        "snapshots_consistent": all(
            all((tool["observed_minute"] == entry["minute"] if tool["ok"]
                 else tool["observed_minute"] is None)
                and (tool["latest_sample_minute"] is None
                     or tool["latest_sample_minute"] <= entry["minute"])
                and (tool["latest_log_minute"] is None
                     or tool["latest_log_minute"] <= entry["minute"])
                for tool in entry["tools"])
            for entry in observations),
        "final_recovery_seen_by_all": all(
            entries[-1]["status"] == scenario.events[-1]["status"]
            and entries[-1]["minute"] == scenario.events[-1]["minute"]
            for entries in by_client.values()),
        "wall_clock_paced": elapsed_seconds >= (len(scenario.events) - 1)
                            * interval_seconds * 0.8,
    }
    return {"scenario_id": scenario_id, "passed": all(checks.values()),
            "checks": checks, "clients": clients, "polls": len(observations),
            "max_in_flight": max_in_flight, "interval_seconds": interval_seconds,
            "poll_interval_seconds": poll_interval_seconds,
            "elapsed_seconds": round(elapsed_seconds, 3),
            "published_minutes": published_minutes,
            "observations": sorted(observations, key=lambda item: (item["minute"], item["client"]))}
