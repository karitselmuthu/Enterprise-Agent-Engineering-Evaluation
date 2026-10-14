"""Demonstrate resuming an investigation after constructing a new agent."""
from pathlib import Path
from tempfile import TemporaryDirectory

from src.memory.agent import StatefulIncidentAgent

if __name__ == "__main__":
    with TemporaryDirectory() as directory:
        path = Path(directory) / "investigations.sqlite3"
        first = StatefulIncidentAgent(path)
        print(first.investigate("demo", "Investigate INC-001").answer)
        first.long_term.add_memory("demo", "fact", "Pool utilization reached 95%",
                                   approved=True)
        restarted = StatefulIncidentAgent(path)
        print(restarted.resume("demo"))
        print(restarted.investigate("demo", "Continue investigation").answer)
