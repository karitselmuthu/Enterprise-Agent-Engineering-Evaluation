"""Run the sample agent from the repository root."""
import argparse
import json
from src.agents.runtime import IncidentAgent

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("incident_id")
    state = IncidentAgent().run(parser.parse_args().incident_id)
    print(json.dumps({"answer": state.answer, "tool_results": [
        {"name": r.name, "ok": r.ok, "error": r.error} for r in state.tool_results]}, indent=2))

if __name__ == "__main__":
    main()
