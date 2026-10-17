"""Normalize user-supplied JSONL logs without creating evaluation labels."""

from datetime import datetime, timedelta
import json
from pathlib import Path


def normalize_public_logs(source: str | Path, mapping: dict) -> list[dict]:
    """Map source fields to timestamp, service, severity, and message."""
    fields = mapping.get("fields")
    if (not isinstance(fields, dict)
            or set(fields) != {"timestamp", "service", "severity", "message"}
            or any(not isinstance(value, str) or not value for value in fields.values())):
        raise ValueError("Mapping needs four nonempty source field names")
    severity_map = mapping.get("severity_map", {})
    if not isinstance(severity_map, dict):
        raise ValueError("severity_map must be an object")
    records = []
    for line_number, line in enumerate(Path(source).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict):
                raise ValueError("line must be an object")
            values = {name: raw[source_name] for name, source_name in fields.items()}
            if any(not isinstance(value, str) or not value for value in values.values()):
                raise ValueError("mapped values must be nonempty strings")
            timestamp = datetime.fromisoformat(values["timestamp"].replace("Z", "+00:00"))
            if timestamp.tzinfo is None or timestamp.utcoffset() != timedelta(0):
                raise ValueError("timestamp must be UTC")
            severity = severity_map.get(values["severity"], values["severity"])
            if severity not in {"INFO", "WARN", "ERROR"}:
                raise ValueError("severity must map to INFO, WARN, or ERROR")
            records.append({"timestamp": timestamp.isoformat().replace("+00:00", "Z"),
                            "service": values["service"], "severity": severity,
                            "message": values["message"]})
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ValueError(f"Invalid public log at line {line_number}: {exc}") from exc
    if not records:
        raise ValueError("No public logs found")
    return sorted(records, key=lambda item: (item["timestamp"], item["service"],
                                             item["message"]))
