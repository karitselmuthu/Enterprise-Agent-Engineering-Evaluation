"""Build timestamped application log entries."""


def build_logs(spec: list, timestamp: str) -> list[dict]:
    if not isinstance(spec, list):
        raise ValueError("Logs must be a list")
    entries = []
    for item in spec:
        if (not isinstance(item, dict) or set(item) != {"severity", "message"}
                or item["severity"] not in {"INFO", "WARN", "ERROR"}
                or not isinstance(item["message"], str) or not item["message"]):
            raise ValueError("Invalid synthetic log entry")
        entries.append({"timestamp": timestamp, **item})
    return entries
