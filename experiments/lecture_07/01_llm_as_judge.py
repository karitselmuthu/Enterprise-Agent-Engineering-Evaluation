"""Run an optional local model judge on a fixed incident answer."""

import argparse
from src.evaluation.llm_judge import JudgeRequest, OllamaJudge


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="Installed Ollama model name")
    args = parser.parse_args()
    request = JudgeRequest(
        question="What caused incident INC-001?",
        answer="The incident was caused by an overloaded database connection pool.",
        reference="Database connection pool exhaustion caused the incident.",
        evidence="Incident record: suspected cause is connection pool exhaustion.",
    )
    print(OllamaJudge(args.model).evaluate(request))


if __name__ == "__main__":
    main()
