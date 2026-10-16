"""Combine scenario and recovery reports into a ten-metric summary."""

import argparse
import json
from pathlib import Path

from src.evaluation.operational_metrics import build_operational_metrics
from src.evaluation.reports import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scenarios", type=Path,
                        default=Path("reports/scenario_results/scenario_validation.json"))
    parser.add_argument("--reliability", type=Path,
                        default=Path("reports/scenario_results/reliability.json"))
    parser.add_argument("--output", type=Path,
                        default=Path("reports/scenario_results/operational_metrics.json"))
    args = parser.parse_args()
    report = build_operational_metrics(json.loads(args.scenarios.read_text(encoding="utf-8")),
                                       json.loads(args.reliability.read_text(encoding="utf-8")))
    report["source_reports"] = {"scenarios": str(args.scenarios),
                                "reliability": str(args.reliability)}
    write_report(args.output, report)
    measured = sum(item["value"] is not None for item in report["metrics"].values())
    print(f"Operational metrics: {measured}/10 measured; "
          f"scenario_count={report['scenario_count']}; report={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
