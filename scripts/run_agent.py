"""Run the sample agent from the repository root."""
import argparse
import json
from src.agents.runtime import IncidentAgent

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("request", help="Incident ID or a service health request")
    parser.add_argument("--ollama-model", help="Use a local Ollama tool-capable model")
    args = parser.parse_args()
    if args.ollama_model:
        from src.llm.local_backend import OllamaBackend
        agent = IncidentAgent(backend=OllamaBackend(args.ollama_model))
    else:
        agent = IncidentAgent()
    state = agent.run(args.request)
    print(json.dumps({"answer": state.answer, "tool_results": [
        {"name": r.name, "ok": r.ok, "error": r.error} for r in state.tool_results],
        "trace": state.trace}, indent=2))

if __name__ == "__main__":
    main()
