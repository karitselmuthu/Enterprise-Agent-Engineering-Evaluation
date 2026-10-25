"""Durable, HMAC chained governance metadata without prompts or tool payloads."""

from datetime import datetime, timezone
import fcntl
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
from typing import Any


class AuditIntegrityError(RuntimeError):
    pass


class AuditSink:
    def __init__(self, path: str | Path, key: bytes):
        if not key or len(key) < 32:
            raise ValueError("Audit HMAC key must contain at least 32 bytes")
        self.path = Path(path)
        self.key = key

    def _mac(self, event: dict[str, Any]) -> str:
        data = json.dumps(event, sort_keys=True, separators=(",", ":"),
                          allow_nan=False).encode("utf-8")
        return hmac.new(self.key, data, sha256).hexdigest()

    def _read_verified(self, stream) -> list[dict[str, Any]]:
        stream.seek(0)
        records = []
        previous = "0" * 64
        for line in stream:
            try:
                record = json.loads(line)
                mac = record.pop("mac")
                if (record["sequence"] != len(records) + 1
                        or record["previous_mac"] != previous
                        or not hmac.compare_digest(mac, self._mac(record))):
                    raise AuditIntegrityError("Audit chain mismatch")
                record["mac"] = mac
            except (ValueError, KeyError, TypeError) as exc:
                raise AuditIntegrityError("Invalid audit record") from exc
            records.append(record)
            previous = mac
        return records

    def verify(self) -> list[dict[str, Any]]:
        with self.path.open("r", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_SH)
            return self._read_verified(stream)

    def append(self, *, actor_id: str, operation: str, environment: str,
               decision: str, reason: str, approval_reference: str | None,
               outcome: str | None = None, duration_ms: float | None = None) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(self.path, os.O_RDWR | os.O_CREAT, 0o600)
        with os.fdopen(descriptor, "r+", encoding="utf-8") as stream:
            fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
            records = self._read_verified(stream)
            record = {
                "sequence": len(records) + 1,
                "previous_mac": records[-1]["mac"] if records else "0" * 64,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "policy_version": "governance-v1",
                "actor_id": actor_id,
                "operation": operation,
                "environment": environment,
                "decision": decision,
                "reason": reason,
                "approval_reference": approval_reference,
                "outcome": outcome,
                "duration_ms": duration_ms,
            }
            record["mac"] = self._mac(record)
            stream.seek(0, os.SEEK_END)
            stream.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            stream.flush()
            os.fsync(stream.fileno())
            return record
