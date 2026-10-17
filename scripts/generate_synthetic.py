"""Generate five public scenarios from dependency-free YAML blueprints."""

import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from simulation.generators import DEFAULT_BLUEPRINTS, build_synthetic_records
from simulation.scenario_loader import load_scenarios


DEFAULT_OUTPUT = Path("data/synthetic/scenarios.jsonl")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--blueprints", type=Path, default=DEFAULT_BLUEPRINTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    records = build_synthetic_records(args.blueprints)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent,
                            prefix=".synthetic-", suffix=".jsonl", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write("".join(json.dumps(item, sort_keys=True) + "\n"
                             for item in records))
    try:
        loaded = load_scenarios(temporary)
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Generated {len(loaded)} public scenarios: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
