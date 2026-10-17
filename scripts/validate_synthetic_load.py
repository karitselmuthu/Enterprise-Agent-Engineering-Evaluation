"""Run and record a small synthetic snapshot consistency workload."""

import argparse
from pathlib import Path

from src.evaluation.reports import write_report
from src.evaluation.synthetic_load import validate_synthetic_load


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--concurrent", type=int, default=10)
    parser.add_argument("--sequential", type=int, default=50)
    parser.add_argument("--output", type=Path,
                        default=Path("reports/reliability/synthetic_load.json"))
    args = parser.parse_args()
    report = validate_synthetic_load(args.concurrent, args.sequential)
    write_report(args.output, report)
    print(f"Synthetic load passed={report['passed']}; "
          f"concurrent={report['concurrent_count']}; "
          f"sequential={report['sequential_count']}; report={args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
