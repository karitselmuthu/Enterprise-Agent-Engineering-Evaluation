"""Deny by default."""
def require_allowed(name: str, allowed: frozenset[str]) -> None:
    if name not in allowed:
        raise PermissionError(f"Tool not permitted: {name}")
