"""Compare two tool-selection requests."""
from src.agents.runtime import IncidentAgent

if __name__ == "__main__":
    agent = IncidentAgent()
    for request in ("Investigate INC-001", "Check health of service api"):
        state = agent.run(request)
        print(request)
        print(state.trace)
        print(state.answer)
