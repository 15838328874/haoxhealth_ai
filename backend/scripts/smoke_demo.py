"""Manual smoke test sample for local verification.

Usage:
    cd backend
    python scripts/smoke_demo.py
"""

from __future__ import annotations

import json
import requests

BASE = "http://127.0.0.1:8000/api"


def show(title: str, data):
    print(f"\n=== {title} ===")
    print(json.dumps(data, ensure_ascii=False, indent=2) if isinstance(data, dict) else data)


def main() -> None:
    show("health", requests.get(f"{BASE}/health", timeout=5).json())
    show("tools", requests.get(f"{BASE}/tools", timeout=5).json())

    resp = requests.post(
        f"{BASE}/tools/execute",
        timeout=10,
        json={
            "tool_name": "amap_route_plan",
            "arguments": {"origin": "杭州东站", "destination": "西湖", "mode": "driving"},
            "session_id": "demo-session",
            "idempotency_key": "manual-001",
        },
    )
    show("tool_execute", resp.json())

    with requests.post(
        f"{BASE}/chat/demo-session/stream",
        json={"message": "从杭州东站到西湖怎么走", "tool_mode": "auto"},
        stream=True,
        timeout=20,
    ) as stream_resp:
        print("\n=== chat_stream events ===")
        for line in stream_resp.iter_lines(decode_unicode=True):
            if line:
                print(line)


if __name__ == "__main__":
    main()
