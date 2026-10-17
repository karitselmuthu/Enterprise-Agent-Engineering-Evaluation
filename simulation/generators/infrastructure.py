"""Validate stable server and service identities in synthetic scenarios."""


def build_infrastructure(spec: dict) -> dict[str, str]:
    if not isinstance(spec, dict):
        raise ValueError("Incident infrastructure must be an object")
    fields = ("server_id", "service")
    if any(not isinstance(spec.get(field), str) or not spec[field] for field in fields):
        raise ValueError("Incident needs a server_id and service")
    return {field: spec[field] for field in fields}
