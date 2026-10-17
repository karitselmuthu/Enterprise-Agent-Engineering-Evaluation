"""Deterministic synthetic observations from public scenario blueprints."""

from datetime import datetime, timedelta
from pathlib import Path

from simulation.generators.incidents import build_incident
from simulation.generators.logs import build_logs
from simulation.generators.metrics import build_metrics
from simulation.scenario_loader import load_blueprint


DEFAULT_BLUEPRINTS = Path(__file__).resolve().parents[1] / "scenarios"


def build_synthetic_records(directory: str | Path = DEFAULT_BLUEPRINTS) -> list[dict]:
    paths = sorted(Path(directory).glob("*.yaml"))
    if not paths:
        raise ValueError("No scenario blueprints found")
    records = []
    seen = set()
    for path in paths:
        blueprint = load_blueprint(path)
        identifier = blueprint.get("scenario_id")
        if not isinstance(identifier, str) or not identifier or identifier in seen:
            raise ValueError(f"Invalid or duplicate scenario ID in {path}")
        seen.add(identifier)
        try:
            start = datetime.fromisoformat(blueprint["start_at"].replace("Z", "+00:00"))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid start time in {path}") from exc
        if start.tzinfo is None or start.utcoffset() != timedelta(0):
            raise ValueError(f"Start time must be UTC in {path}")
        incident = build_incident(identifier, blueprint.get("incident"))
        timeline = blueprint.get("timeline")
        if not isinstance(timeline, list) or not timeline:
            raise ValueError(f"Missing timeline in {path}")
        events = []
        previous = -1
        for step in timeline:
            if not isinstance(step, dict):
                raise ValueError(f"Invalid timeline step in {path}")
            minute = step.get("minute")
            if not isinstance(minute, int) or isinstance(minute, bool) or minute <= previous:
                raise ValueError(f"Timeline minutes must increase in {path}")
            timestamp = (start + timedelta(minutes=minute)).isoformat().replace("+00:00", "Z")
            events.append({"minute": minute, "timestamp": timestamp,
                           "status": step.get("status"),
                           "metrics": build_metrics(step.get("metrics"), timestamp),
                           "logs": build_logs(step.get("logs"), timestamp),
                           "faults": step.get("faults", [])})
            previous = minute
        if events[0]["minute"] != 0:
            raise ValueError(f"Timeline must start at zero in {path}")
        records.append({"scenario_id": identifier, "incident": incident,
                        "allowed_tools": blueprint.get("allowed_tools", [
                            "get_incident_record", "get_server_metrics", "get_application_logs"]),
                        "events": events})
    return records
