"""Inject a controlled fault into the optional local Compose demo."""

import argparse
import json
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("healthy", "database_failure", "recovered"))
    parser.add_argument("--url", default="http://127.0.0.1:8765")
    args = parser.parse_args()
    parsed = urlsplit(args.url)
    if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}
            or parsed.port is None or parsed.username or parsed.password
            or parsed.path not in {"", "/"} or parsed.query or parsed.fragment):
        parser.error("Live demo URL must use local loopback")
    request = Request(args.url.rstrip("/") + "/control/fault",
                      data=json.dumps({"mode": args.mode}).encode("utf-8"),
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=2) as response:
        print(response.read().decode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
