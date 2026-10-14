"""Agent interface."""
from typing import Protocol
from .state import AgentState
class Agent(Protocol):
    def run(self, incident_id: str) -> AgentState: ...
