"""Run the initial operational stress probes and write a JSON report."""

import argparse
from pathlib import Path

from src.evaluation.reliability import run_reliability_workload
from src.evaluation.reports import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrent", type=int, default=10)
    parser.add_argument("--sequential", type=int, default=50)
    parser.add_argument("--output", type=Path,
                        default=Path("reports/scenario_results/reliability.json"))
    args = parser.parse_args()
    report = run_reliability_workload(args.concurrent, args.sequential)
    write_report(args.output, report)
    print(f"Reliability passed={report['passed']}; "
          f"concurrent={report['concurrent_count']}; "
          f"sequential={report['sequential_count']}; "
          f"report={args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
