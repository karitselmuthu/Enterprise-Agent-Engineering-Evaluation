"""Response backend interface."""
from typing import Protocol
class Backend(Protocol):
    def generate(self, incident: dict) -> str: ...
