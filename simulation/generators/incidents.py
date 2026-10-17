"""Build public incident alerts without evaluation labels."""

from simulation.generators.infrastructure import build_infrastructure


def build_incident(identifier: str, spec: dict) -> dict:
    identity = build_infrastructure(spec)
    if (not isinstance(spec.get("summary"), str) or not spec["summary"]
            or spec.get("severity") not in {"P1", "P2", "P3", "P4"}
            or not isinstance(spec.get("alert_at_minute", 0), int)
            or isinstance(spec.get("alert_at_minute", 0), bool)
            or spec.get("alert_at_minute", 0) < 0):
        raise ValueError("Invalid synthetic incident alert")
    return {"id": identifier, **identity, "summary": spec["summary"],
            "severity": spec["severity"],
            "alert_at_minute": spec.get("alert_at_minute", 0)}
