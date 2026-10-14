"""Generate and test a log analyzer inside Docker."""
import os
from src.coding_agents.code_agent import LogAnalysisCodeAgent, OllamaCodeGenerator

if __name__ == "__main__":
    model = os.getenv("OLLAMA_MODEL")
    generator = OllamaCodeGenerator(model) if model else None
    report = LogAnalysisCodeAgent(generator=generator).run(
        "Generate a Python script to analyze application logs",
        "INFO service started\nWARN request slow\nERROR connection failed\n",
    )
    print(report)
