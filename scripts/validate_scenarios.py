"""Write a four-check scenario evaluation report."""

from pathlib import Path

from src.evaluation.reports import write_report
from src.evaluation.scenario_validation import evaluate_scenarios


def main() -> int:
    report = evaluate_scenarios()
    output = Path("reports/scenario_results/scenario_validation.json")
    write_report(output, report)
    print(f"{report['scenario_count']} scenarios; foundation={report['foundation_passed']}; "
          f"tools={report['tool_selection_rate']:.2f}; "
          f"evidence={report['evidence_retrieval_rate']:.2f}; "
          f"cause proxy={report['root_cause_supported_proxy_rate']:.2f}; "
          f"recommendation cue={report['recommendation_cue_rate']:.2f}; "
          f"report={output}")
    return 0 if report["foundation_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
