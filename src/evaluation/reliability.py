"""Small, reproducible reliability workload for the synthetic agent stack."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from multiprocessing import get_context
from statistics import median
from threading import Barrier, Lock
from time import monotonic, sleep
from unittest.mock import patch

from simulation.adapters.tools import replay_tools
from simulation.clock import VirtualClock
from simulation.engine import ReplayEngine
from simulation.scenario_loader import load_scenarios
from src.agents.simulation_agent import SimulationInvestigator
from src.mcp.client import MCPIncidentAgent
from src.mcp.server import mcp
from src.tools.executor import ToolExecutor, ToolResult
from src.tools.registry import Tool, ToolRegistry

from .simulation_eval import load_ground_truth


def _investigate(identifier: str, minute: int) -> dict:
    scenario = load_scenarios()[identifier]
    engine = ReplayEngine(scenario, VirtualClock(minute))
    started = monotonic()
    state = SimulationInvestigator(replay_tools(engine)).run(identifier)
    return {"scenario_id": identifier, "answer": state.answer,
            "calls": [(result.name, result.error_code) for result in state.tool_results],
            "duration_ms": round((monotonic() - started) * 1000, 3)}


def _bounded_worker(identifier: str, minute: int, delay_seconds: float, connection) -> None:
    try:
        scenario = load_scenarios()[identifier]
        tools = replay_tools(ReplayEngine(scenario, VirtualClock(minute)))

        class DelayedTools:
            def execute(self, name, arguments):
                if name == "get_server_metrics":
                    sleep(delay_seconds)
                return tools.execute(name, arguments)

        connection.send({"stage": "ready"})
        state = SimulationInvestigator(DelayedTools()).run(identifier)
        connection.send({"stage": "completed", "answer": state.answer})
    except Exception as exc:
        connection.send({"stage": "error", "error": str(exc)})
    finally:
        connection.close()


def run_bounded_investigation(identifier: str, minute: int,
                              delay_seconds: float, timeout_seconds: float) -> dict:
    if delay_seconds < 0 or timeout_seconds <= 0:
        raise ValueError("delay must be nonnegative and timeout must be positive")
    context = get_context("spawn")
    parent, child = context.Pipe(duplex=False)
    process = context.Process(target=_bounded_worker,
                              args=(identifier, minute, delay_seconds, child))
    process.start()
    child.close()
    try:
        if not parent.poll(5):
            return {"status": "startup_timeout"}
        ready = parent.recv()
        if ready["stage"] != "ready":
            return {"status": "error", "detail": ready}
        process.join(timeout_seconds)
        if process.is_alive():
            return {"status": "timed_out"}
        return {"status": "completed", "detail": parent.recv()} if parent.poll() \
            else {"status": "error", "detail": "worker exited without result"}
    finally:
        if process.is_alive():
            process.terminate()
            process.join(1)
            if process.is_alive():
                process.kill()
                process.join()
        parent.close()


def _slow_tool_probe() -> bool:
    registry = ToolRegistry()

    def slow_metric(server_id: str) -> dict:
        sleep(0.05)
        return {"server_id": server_id}

    registry.register(Tool("slow_metric", "Delayed synthetic metric", {
        "type": "object", "properties": {"server_id": {"type": "string"}},
        "required": ["server_id"], "additionalProperties": False}, slow_metric))
    result = ToolExecutor(registry, frozenset({"slow_metric"})).execute(
        "slow_metric", {"server_id": "prod-app-001"}, timeout_seconds=0.005)
    return result.error_code == "timeout"


def _malformed_response_probe() -> bool:
    scenario = load_scenarios()["SIM-001"]
    underlying = replay_tools(ReplayEngine(scenario, VirtualClock(10)))

    class MalformedTools:
        def execute(self, name, arguments):
            if name == "get_server_metrics":
                return ToolResult(name, True, content={"observed_minute": 10, "samples": [
                    {"minute": 10, "timestamp": "2026-10-14T10:10:00Z",
                     "cpu_percent": "corrupt", "memory_percent": 50, "disk_percent": 45}]})
            return underlying.execute(name, arguments)

    state = SimulationInvestigator(MalformedTools()).run("SIM-001")
    return (any(result.error_code == "malformed_tool_response"
                for result in state.tool_results)
            and "unavailable" in state.answer.casefold())


async def _mcp_recovery_probe() -> bool:
    class UnavailableClient:
        def __init__(self, _server):
            pass

        async def __aenter__(self):
            raise ConnectionError("temporary MCP outage")

        async def __aexit__(self, *_args):
            return None

    with patch("src.mcp.client.Client", UnavailableClient):
        failed = await MCPIncidentAgent(mcp).run("Investigate INC-001")
    recovered = await MCPIncidentAgent(mcp).run("Investigate INC-001")
    return (failed.tool_results[0].error_code == "mcp_unavailable"
            and recovered.tool_results[0].ok)


def run_reliability_workload(concurrent: int = 10, sequential: int = 50) -> dict:
    if not isinstance(concurrent, int) or isinstance(concurrent, bool) or concurrent < 2:
        raise ValueError("concurrent must be an integer of at least two")
    if not isinstance(sequential, int) or isinstance(sequential, bool) or sequential < 1:
        raise ValueError("sequential must be a positive integer")
    labels = load_ground_truth()
    identifiers = sorted(labels)
    expected = {identifier: _investigate(identifier, labels[identifier]["evaluation_minute"])
                for identifier in identifiers}
    concurrent_ids = [identifiers[index % len(identifiers)] for index in range(concurrent)]
    start_barrier = Barrier(concurrent)
    active_lock = Lock()
    active = 0
    peak_active = 0

    def concurrent_request(identifier: str) -> dict:
        nonlocal active, peak_active
        with active_lock:
            active += 1
            peak_active = max(peak_active, active)
        # Every request is in flight before the investigations begin.
        start_barrier.wait(timeout=5)
        try:
            return _investigate(identifier, labels[identifier]["evaluation_minute"])
        finally:
            with active_lock:
                active -= 1

    started = monotonic()
    with ThreadPoolExecutor(max_workers=concurrent) as pool:
        futures = [pool.submit(concurrent_request, identifier) for identifier in concurrent_ids]
        concurrent_results = [future.result(timeout=5) for future in futures]
    concurrent_elapsed_ms = round((monotonic() - started) * 1000, 3)
    sequential_results = [_investigate(identifier, labels[identifier]["evaluation_minute"])
                          for identifier in (identifiers[index % len(identifiers)]
                                             for index in range(sequential))]
    repeated = [_investigate("SIM-004", 25) for _ in range(5)]
    same = lambda result: (result["answer"], result["calls"])
    checks = {
        "concurrent_investigations": peak_active == concurrent and all(
            same(item) == same(expected[item["scenario_id"]]) for item in concurrent_results),
        "sequential_requests": all(same(item) == same(expected[item["scenario_id"]])
                                   for item in sequential_results),
        "repeated_requests": len({str(same(item)) for item in repeated}) == 1,
        "tool_latency_timeout": _slow_tool_probe(),
        "temporary_mcp_failure_and_recovery": asyncio.run(_mcp_recovery_probe()),
        "malformed_tool_response": _malformed_response_probe(),
        "agent_execution_timeout": run_bounded_investigation("SIM-001", 10, 0.3, 0.03)[
            "status"] == "timed_out",
    }
    durations = sorted(item["duration_ms"] for item in concurrent_results + sequential_results)
    return {"passed": all(checks.values()), "checks": checks,
            "concurrent_count": concurrent, "sequential_count": sequential,
            "peak_in_flight": peak_active,
            "mcp_recovery_attempts": 1,
            "mcp_recovery_successes": int(checks["temporary_mcp_failure_and_recovery"]),
            "repeated_count": len(repeated),
            "concurrent_batch_ms": concurrent_elapsed_ms,
            "median_investigation_ms": round(median(durations), 3),
            "p95_investigation_ms": durations[max(0, int(len(durations) * 0.95) - 1)]}
