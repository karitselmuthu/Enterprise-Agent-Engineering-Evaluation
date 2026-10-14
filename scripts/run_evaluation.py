"""Run the offline Lecture 7 benchmark and write a stable JSON report."""

import argparse
from pathlib import Path

from src.evaluation.benchmarks import load_benchmark, run_benchmark
from src.evaluation.reports import write_report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path,
                        default=Path("data/evaluation_datasets/incident_benchmark.jsonl"))
    parser.add_argument("--output", type=Path,
                        default=Path("reports/lecture_07/benchmark.json"))
    args = parser.parse_args()
    cases, fingerprint = load_benchmark(args.dataset)
    report = run_benchmark(cases, fingerprint)
    write_report(args.output, report)
    print(f"{report['case_count']} cases; passed={report['passed']}; report={args.output}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
