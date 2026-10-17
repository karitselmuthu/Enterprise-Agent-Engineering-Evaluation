"""Validate and normalize a user-provided public JSONL log file."""

import argparse
import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from simulation.importers.public_logs import normalize_public_logs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path, help="User-supplied JSONL file")
    parser.add_argument("--mapping", type=Path, required=True,
                        help="JSON mapping of source field names")
    parser.add_argument("--output", type=Path, required=True,
                        help="Normalized output JSONL path")
    args = parser.parse_args()
    if args.source.resolve() == args.output.resolve():
        parser.error("Output must differ from source")
    mapping = json.loads(args.mapping.read_text(encoding="utf-8"))
    normalized = normalize_public_logs(args.source, mapping)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=args.output.parent,
                            prefix=".public-logs-", suffix=".jsonl", delete=False) as handle:
        temporary = Path(handle.name)
        handle.write("".join(json.dumps(item, sort_keys=True) + "\n"
                             for item in normalized))
    try:
        temporary.replace(args.output)
    finally:
        temporary.unlink(missing_ok=True)
    print(f"Normalized {len(normalized)} public logs: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
