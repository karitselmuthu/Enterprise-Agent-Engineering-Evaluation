"""Tiny SQLite-backed observation service for controlled local fault injection."""

from contextlib import contextmanager
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock
from urllib.parse import parse_qs, urlsplit


INCIDENT_ID = "LIVE-001"
SERVER_ID = "live-app-001"
SERVICE = "payment-service"
MODES = {
    "healthy": ("healthy", 35, 48, 20, "INFO", "Payment service healthy"),
    "database_failure": ("degraded", 82, 73, 210, "ERROR",
                         "Database connection refused; payment requests failing"),
    "recovered": ("resolved", 42, 55, 30, "INFO", "Database available; service recovered"),
}


class LiveStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = Lock()
        with self._connect() as connection:
            connection.execute("CREATE TABLE IF NOT EXISTS events ("
                               "step INTEGER PRIMARY KEY AUTOINCREMENT, "
                               "timestamp TEXT NOT NULL, mode TEXT NOT NULL)")
            count = connection.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            if count == 0:
                self._insert(connection, "healthy")

    @contextmanager
    def _connect(self):
        connection = sqlite3.connect(self.path, timeout=5)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    @staticmethod
    def _insert(connection, mode: str) -> None:
        timestamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        connection.execute("INSERT INTO events (timestamp, mode) VALUES (?, ?)",
                           (timestamp, mode))

    def inject(self, mode: str) -> None:
        if mode not in MODES:
            raise ValueError("Unknown fault mode")
        with self._lock, self._connect() as connection:
            self._insert(connection, mode)

    def events(self) -> list[dict]:
        with self._lock, self._connect() as connection:
            rows = connection.execute(
                "SELECT step, timestamp, mode FROM events ORDER BY step").fetchall()
        return [{"minute": step - 1, "timestamp": timestamp, "mode": mode}
                for step, timestamp, mode in rows]

    def incident(self, incident_id: str) -> dict:
        if incident_id != INCIDENT_ID:
            raise KeyError("Unknown incident")
        latest = self.events()[-1]
        status = MODES[latest["mode"]][0]
        return {"id": INCIDENT_ID, "server_id": SERVER_ID, "service": SERVICE,
                "summary": "Controlled payment service fault demo", "severity": "P2",
                "status": status, "observed_minute": latest["minute"],
                "observed_at": latest["timestamp"]}

    def metrics(self, server_id: str) -> dict:
        if server_id != SERVER_ID:
            raise KeyError("Unknown server")
        events = self.events()
        samples = []
        for event in events:
            _, cpu, memory, latency, _, _ = MODES[event["mode"]]
            samples.append({"minute": event["minute"], "timestamp": event["timestamp"],
                            "cpu_percent": cpu, "memory_percent": memory,
                            "disk_percent": 45, "network_latency_ms": latency})
        return {"server_id": SERVER_ID, "observed_minute": events[-1]["minute"],
                "observed_at": events[-1]["timestamp"], "status": "available",
                "samples": samples}

    def logs(self, service: str) -> dict:
        if service != SERVICE:
            raise KeyError("Unknown service")
        events = self.events()
        entries = []
        for event in events:
            _, _, _, _, severity, message = MODES[event["mode"]]
            entries.append({"minute": event["minute"], "timestamp": event["timestamp"],
                            "server_id": SERVER_ID, "service": SERVICE,
                            "severity": severity, "message": message})
        return {"service": SERVICE, "observed_minute": events[-1]["minute"],
                "observed_at": events[-1]["timestamp"], "entries": entries}


def make_handler(store: LiveStore):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, value: dict) -> None:
            body = json.dumps(value).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            request = urlsplit(self.path)
            if request.path == "/health":
                self._send(200, {"status": "ok"})
                return
            routes = {"/v1/incident": ("incident_id", store.incident),
                      "/v1/metrics": ("server_id", store.metrics),
                      "/v1/logs": ("service", store.logs)}
            if request.path not in routes:
                self._send(404, {"error": "Unknown route"})
                return
            field, method = routes[request.path]
            values = parse_qs(request.query)
            if set(values) != {field} or len(values[field]) != 1:
                self._send(400, {"error": f"Expected {field}"})
                return
            try:
                self._send(200, method(values[field][0]))
            except KeyError as exc:
                self._send(404, {"error": str(exc)})

        def do_POST(self) -> None:
            if self.path != "/control/fault":
                self._send(404, {"error": "Unknown route"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 4096:
                    raise ValueError("Invalid body length")
                body = json.loads(self.rfile.read(length))
                if not isinstance(body, dict) or set(body) != {"mode"}:
                    raise ValueError("Expected mode")
                store.inject(body["mode"])
                self._send(200, {"mode": body["mode"], "step": len(store.events()) - 1})
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                self._send(400, {"error": str(exc)})

        def log_message(self, _format, *_args):
            pass

    return Handler


def main() -> None:
    store = LiveStore(os.environ.get("LIVE_DB_PATH", "/state/live.sqlite3"))
    host = os.environ.get("LIVE_BIND", "0.0.0.0")
    ThreadingHTTPServer((host, 8765), make_handler(store)).serve_forever()


if __name__ == "__main__":
    main()
