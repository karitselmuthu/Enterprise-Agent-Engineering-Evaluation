"""Run the payment database-latency scenario and three fault variants."""

import argparse
from pathlib import Path

from src.evaluation.database_latency_eval import evaluate_database_latency
from src.evaluation.reports import write_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("reports/scenario_results/database_latency.json"))
    args = parser.parse_args()
    report = evaluate_database_latency()
    write_report(args.output, report)
    for item in report["results"]:
        print(f"{item['variant']}: {'PASS' if item['passed'] else 'FAIL'}; "
              f"score={item['score']:.2f}; "
              f"finding={item['finding_status']}; "
              f"database_tool={item['database_tool_status']}")
    print(f"report={args.output}")
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
