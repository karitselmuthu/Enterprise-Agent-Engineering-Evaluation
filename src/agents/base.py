"""Agent interface."""
from typing import Protocol
from .state import AgentState
class Agent(Protocol):
    def run(self, request: str) -> AgentState: ...
