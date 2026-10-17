"""Build timestamped infrastructure metric samples."""

from math import isfinite


FIELDS = ("cpu_percent", "memory_percent", "disk_percent", "network_latency_ms")


def build_metrics(spec: dict | None, timestamp: str) -> dict | None:
    if spec is None:
        return None
    if not isinstance(spec, dict) or set(spec) != set(FIELDS):
        raise ValueError("Metrics need CPU, memory, disk, and network latency")
    for field in FIELDS:
        value = spec[field]
        upper = 100 if field.endswith("percent") else float("inf")
        if (not isinstance(value, (int, float)) or isinstance(value, bool)
                or not isfinite(value) or not 0 <= value <= upper):
            raise ValueError(f"Invalid metric: {field}")
    return {**spec, "timestamp": timestamp}
