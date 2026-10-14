"""Replay and evaluate the public scenarios with private labels."""

from pathlib import Path

from src.evaluation.reports import write_report
from src.evaluation.simulation_eval import run_simulation_evaluation


def main() -> None:
    report = run_simulation_evaluation()
    output = Path("reports/scenario_results/replay.json")
    write_report(output, report)
    print(f"{report['scenario_count']} scenarios; "
          f"tool coverage={report['mean_tool_coverage']:.2f}; "
          f"tool success={report['mean_tool_execution_success']:.2f}; "
          f"literal root-cause phrase rate={report['literal_root_cause_phrase_rate']:.2f}; "
          f"report={output}")


if __name__ == "__main__":
    main()
