"""Load public scenarios only; evaluation labels have a separate loader."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import json
from pathlib import Path
from typing import Any


DEFAULT_SCENARIOS = Path(__file__).resolve().parents[1] / "data/simulation/scenarios.jsonl"
PRIVATE_KEYS = {"root_cause", "expected_findings", "expected_tools", "expected_behavior"}
PUBLIC_TOOL_NAMES = frozenset({"get_incident_record", "get_server_metrics", "get_application_logs"})


@dataclass(frozen=True)
class Scenario:
    scenario_id: str
    incident: dict[str, Any]
    events: tuple[dict[str, Any], ...]
    allowed_tools: frozenset[str]


def _contains_private_key(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(PRIVATE_KEYS.intersection(value)) or any(
            _contains_private_key(child) for child in value.values())
    if isinstance(value, list):
        return any(_contains_private_key(child) for child in value)
    return False


def load_scenarios(path: str | Path = DEFAULT_SCENARIOS) -> dict[str, Scenario]:
    scenarios: dict[str, Scenario] = {}
    for number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
            if not isinstance(raw, dict) or _contains_private_key(raw):
                raise ValueError("private labels or invalid object in public scenario")
            scenario_id, incident, events = raw["scenario_id"], raw["incident"], raw["events"]
            allowed_tools = raw.get("allowed_tools", sorted(PUBLIC_TOOL_NAMES))
            if (not isinstance(scenario_id, str) or not scenario_id
                    or scenario_id in scenarios or not isinstance(incident, dict)
                    or incident.get("id") != scenario_id
                    or not all(isinstance(incident.get(key), str) and incident[key]
                               for key in ("server_id", "service", "summary", "severity"))
                    or not isinstance(incident.get("alert_at_minute", 0), int)
                    or isinstance(incident.get("alert_at_minute", 0), bool)
                    or incident.get("alert_at_minute", 0) < 0
                    or not isinstance(events, list) or not events
                    or not isinstance(allowed_tools, list)
                    or any(not isinstance(tool, str) or tool not in PUBLIC_TOOL_NAMES
                           for tool in allowed_tools)
                    or "get_incident_record" not in allowed_tools):
                raise ValueError("invalid scenario identity or incident")
            previous = -1
            started_at = None
            for event in events:
                if (not isinstance(event, dict)
                        or not isinstance(event.get("minute"), int)
                        or isinstance(event["minute"], bool)
                        or event["minute"] <= previous
                        or not isinstance(event.get("metrics"), (dict, type(None)))
                        or not isinstance(event.get("timestamp"), str)
                        or not isinstance(event.get("logs"), list)
                        or any(not isinstance(log, dict)
                               or not all(isinstance(log.get(key), str)
                                          for key in ("timestamp", "severity", "message"))
                               for log in event["logs"])
                        or event.get("status") not in {
                            "open", "degraded", "recovering", "resolved", "healthy"}
                        or not isinstance(event.get("faults", []), list)):
                    raise ValueError("invalid event timeline")
                try:
                    observed_at = datetime.fromisoformat(event["timestamp"].replace("Z", "+00:00"))
                except ValueError as exc:
                    raise ValueError("invalid event timestamp") from exc
                if observed_at.tzinfo is None or observed_at.utcoffset() != timedelta(0):
                    raise ValueError("event timestamp must be UTC")
                if started_at is None:
                    started_at = observed_at
                if (observed_at != started_at + timedelta(minutes=event["minute"])
                        or event["metrics"] is not None
                        and event["metrics"].get("timestamp") != event["timestamp"]
                        or any(log["timestamp"] != event["timestamp"] for log in event["logs"])):
                    raise ValueError("event timestamps must match virtual minutes")
                previous = event["minute"]
            if events[0]["minute"] != 0:
                raise ValueError("timeline must start at minute zero")
            scenarios[scenario_id] = Scenario(scenario_id, incident, tuple(events),
                                              frozenset(allowed_tools))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"Invalid public scenario line {number}: {exc}") from exc
    if not scenarios:
        raise ValueError("No public scenarios found")
    return scenarios
