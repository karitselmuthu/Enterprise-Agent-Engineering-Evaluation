"""Run Mode B paced polling and concurrency acceptance checks."""

import argparse
import asyncio
from pathlib import Path

from src.evaluation.live_validation import validate_mode_b
from src.evaluation.reports import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="SIM-004")
    parser.add_argument("--interval", type=float, default=0.05,
                        help="Wall seconds between published scenario events")
    parser.add_argument("--poll-interval", type=float, default=0.01,
                        help="Wall seconds between each client's polls")
    parser.add_argument("--clients", type=int, default=3)
    parser.add_argument("--output", type=Path,
                        default=Path("reports/scenario_results/mode_b_validation.json"))
    args = parser.parse_args()
    report = asyncio.run(validate_mode_b(args.scenario, args.interval,
                                         args.poll_interval, args.clients))
    write_report(args.output, report)
    print(f"Mode B validation passed={report['passed']}; clients={report['clients']}; "
          f"polls={report['polls']}; max_in_flight={report['max_in_flight']}; "
          f"elapsed={report['elapsed_seconds']}s; report={args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
