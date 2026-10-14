"""Run replay acceptance checks and write an inspectable report."""

import argparse
import json
from pathlib import Path

from src.evaluation.replay_validation import capture_replay, validate_mode_a
from src.evaluation.reports import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenario", default="SIM-004", help="Scenario ID to inspect")
    parser.add_argument("--minute", type=int, help="Inspect one virtual minute instead of validation")
    parser.add_argument("--output", type=Path,
                        default=Path("reports/scenario_results/mode_a_validation.json"))
    args = parser.parse_args()
    if args.minute is not None:
        print(json.dumps(capture_replay(args.scenario, args.minute), indent=2))
        return 0
    report = validate_mode_a()
    write_report(args.output, report)
    print(f"Mode A validation passed={report['passed']}; report={args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
