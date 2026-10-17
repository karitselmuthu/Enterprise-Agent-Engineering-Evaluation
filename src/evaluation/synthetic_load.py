"""Small reproducible read workload for generated public scenarios."""

from concurrent.futures import ThreadPoolExecutor
from time import perf_counter

from simulation.scenario_loader import load_scenarios
from simulation.state_manager import SimulationStateManager


def validate_synthetic_load(concurrent: int = 10, sequential: int = 50) -> dict:
    if (not isinstance(concurrent, int) or isinstance(concurrent, bool) or concurrent <= 0
            or not isinstance(sequential, int) or isinstance(sequential, bool)
            or sequential <= 0):
        raise ValueError("Workload counts must be positive integers")
    manager = SimulationStateManager(load_scenarios("data/synthetic/scenarios.jsonl"))
    manager.seek("SYN-004", 10)

    def read_once(_index: int) -> bool:
        tools = manager.tools("SYN-004")
        metrics = tools.execute("get_server_metrics", {"server_id": "prod-payment-004"})
        logs = tools.execute("get_application_logs", {"service": "payment-service"})
        return (metrics.ok and logs.ok
                and metrics.content["observed_minute"] == 10
                and logs.content["observed_minute"] == 10
                and len(metrics.content["samples"]) == 3
                and len(logs.content["entries"]) == 3)

    started = perf_counter()
    with ThreadPoolExecutor(max_workers=concurrent) as pool:
        concurrent_results = list(pool.map(read_once, range(concurrent)))
    concurrent_ms = round((perf_counter() - started) * 1000, 3)
    started = perf_counter()
    sequential_results = [read_once(index) for index in range(sequential)]
    sequential_ms = round((perf_counter() - started) * 1000, 3)
    return {"passed": all(concurrent_results + sequential_results),
            "concurrent_count": concurrent, "sequential_count": sequential,
            "concurrent_successes": sum(concurrent_results),
            "sequential_successes": sum(sequential_results),
            "concurrent_elapsed_ms": concurrent_ms,
            "sequential_elapsed_ms": sequential_ms,
            "scope": "Local synthetic tool reads; not an enterprise capacity benchmark"}
