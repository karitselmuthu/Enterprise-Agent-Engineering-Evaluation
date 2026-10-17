"""User data import stays separate from incident labels and replay fixtures."""

import json
from pathlib import Path
import tempfile
import unittest

from simulation.importers.public_logs import normalize_public_logs


class PublicLogImportTests(unittest.TestCase):
    def test_mapping_normalizes_and_orders_user_logs(self):
        mapping = json.loads(Path("configs/public_logs.example.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.jsonl"
            source.write_text("\n".join(json.dumps(item) for item in (
                {"timestamp": "2026-10-17T10:05:00Z", "service": "api",
                 "level": "WARNING", "message": "slow"},
                {"timestamp": "2026-10-17T10:00:00Z", "service": "api",
                 "level": "DEBUG", "message": "ready"})))
            records = normalize_public_logs(source, mapping)
            self.assertEqual([item["message"] for item in records], ["ready", "slow"])
            self.assertEqual(records[1]["severity"], "WARN")
            self.assertEqual(set(records[0]), {"timestamp", "service", "severity", "message"})

    def test_invalid_timestamp_and_severity_rejected(self):
        mapping = json.loads(Path("configs/public_logs.example.json").read_text())
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "raw.jsonl"
            source.write_text(json.dumps({"timestamp": "2026-10-17T10:00:00",
                "service": "api", "level": "INFO", "message": "ready"}) + "\n")
            with self.assertRaisesRegex(ValueError, "line 1"):
                normalize_public_logs(source, mapping)
            source.write_text(json.dumps({"timestamp": "2026-10-17T10:00:00Z",
                "service": "api", "level": "UNKNOWN", "message": "ready"}) + "\n")
            with self.assertRaisesRegex(ValueError, "severity"):
                normalize_public_logs(source, mapping)


if __name__ == "__main__":
    unittest.main()
