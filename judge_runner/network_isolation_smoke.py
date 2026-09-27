"""Fail unless submitted judge code is isolated from the backend network."""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path


def main() -> None:
    token_path = Path(
        os.environ.get("JUDGE_RUNNER_AUTH_TOKEN_FILE", "/run/secrets/judge_runner_token")
    )
    token = token_path.read_text(encoding="utf-8").replace("\r", "").strip()
    if not token:
        raise SystemExit("judge isolation smoke failed: runner token is empty")

    submitted_code = """import socket
try:
    socket.create_connection(("backend", 8000), 0.5)
    print("reachable")
except Exception:
    print("blocked")
"""
    payload = {
        "language": "python",
        "code": submitted_code,
        "tests": [{"input": "", "expected": "blocked"}],
    }
    request = urllib.request.Request(
        "http://127.0.0.1:8090/execute",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=10) as response:
        result = json.load(response)
    if result.get("passed") is not True:
        raise SystemExit("judge isolation smoke failed: backend was reachable")
    print("Judge network isolation smoke passed.")


if __name__ == "__main__":
    main()
