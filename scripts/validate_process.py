"""Print repeatability and process evidence checks for replay investigations."""

import argparse
from pathlib import Path

from src.evaluation.process_validation import evaluate_repeatability
from src.evaluation.reports import write_report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trials", type=int, default=5)
    parser.add_argument("--output", type=Path,
                        default=Path("reports/scenario_results/process_validation.json"))
    args = parser.parse_args()
    report = evaluate_repeatability(args.trials)
    write_report(args.output, report)
    print(f"Process proxy: {report['scenario_count']} scenarios x {args.trials} trials; "
          f"pass@1={report['pass_at_1_proxy_rate']:.2f}; "
          f"all-success={report['all_success_proxy_rate']:.2f}; "
          f"report={args.output}")
    if report["all_success_proxy_rate"] < 1:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
