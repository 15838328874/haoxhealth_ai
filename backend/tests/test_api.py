from __future__ import annotations

import json
import time
from collections.abc import AsyncGenerator

from fastapi.testclient import TestClient

from app.api.routes import engine
from app.main import app


client = TestClient(app)


def _parse_sse(raw_text: str) -> list[tuple[str, dict]]:
    events: list[tuple[str, dict]] = []
    for block in raw_text.split("\n\n"):
        if not block.strip():
            continue
        event = None
        data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line.replace("event: ", "", 1)
            if line.startswith("data: "):
                data = json.loads(line.replace("data: ", "", 1))
        if event and data is not None:
            events.append((event, data))
    return events


def test_health_and_tools_listing() -> None:
    health = client.get("/api/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    tools = client.get("/api/tools")
    assert tools.status_code == 200
    names = {item["name"] for item in tools.json()["data"]["tools"]}
    assert "amap_route_plan" in names
    assert "kb_search" in names


def test_cors_preflight_for_chat_stream() -> None:
    response = client.options(
        "/api/chat/demo-session/stream",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"


def test_tool_execute_and_validation() -> None:
    ok = client.post(
        "/api/tools/execute",
        json={
            "tool_name": "amap_route_plan",
            "arguments": {"origin": "杭州东站", "destination": "西湖", "mode": "driving"},
            "session_id": "s_001",
            "idempotency_key": "req_001",
        },
    )
    assert ok.status_code == 200
    payload = ok.json()["data"]
    assert payload["tool_name"] == "amap_route_plan"
    assert payload["result"]["distance_m"] > 0

    bad = client.post(
        "/api/tools/execute",
        json={
            "tool_name": "amap_route_plan",
            "arguments": {"origin": "", "destination": "西湖", "mode": "driving"},
            "session_id": "s_001",
            "idempotency_key": "req_002",
        },
    )
    assert bad.status_code == 400


def test_chat_stream_auto_tool_call() -> None:
    with client.stream(
        "POST",
        "/api/chat/demo-session/stream",
        json={"message": "从杭州东站到西湖怎么走", "tool_mode": "auto"},
    ) as response:
        assert response.status_code == 200
        body = "".join(chunk for chunk in response.iter_text())

    events = _parse_sse(body)
    event_names = [name for name, _ in events]
    assert "message_start" in event_names
    assert "tool_call_start" in event_names
    assert "tool_call_result" in event_names
    assert "message_delta" in event_names
    assert "message_end" in event_names


def test_chat_stream_passes_model_params_to_dashscope_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    async def fake_stream_chat(**kwargs) -> AsyncGenerator[str, None]:
        captured.update(kwargs)
        yield "ok"

    monkeypatch.setattr(engine.llm_client, "stream_chat", fake_stream_chat)

    with client.stream(
        "POST",
        "/api/chat/demo-session/stream",
        json={"message": "测试模型透传", "model": "qwen-plus", "temperature": 0.2, "max_tokens": 256},
    ) as response:
        assert response.status_code == 200
        body = "".join(chunk for chunk in response.iter_text())

    events = _parse_sse(body)
    assert any(name == "message_delta" for name, _ in events)
    assert captured["model"] == "qwen-plus"
    assert captured["temperature"] == 0.2
    assert captured["max_tokens"] == 256


def test_research_job_lifecycle() -> None:
    created = client.post(
        "/api/research/jobs",
        json={
            "session_id": "demo-session",
            "query": "AI医疗监管变化",
            "max_steps": 2,
            "max_tool_calls": 10,
            "max_tokens": 8000,
            "timeout_sec": 60,
        },
    )
    assert created.status_code == 200
    job_id = created.json()["data"]["job_id"]

    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        poll = client.get(f"/api/research/jobs/{job_id}")
        assert poll.status_code == 200
        status = poll.json()["data"]["status"]
        if status == "completed":
            break
        time.sleep(0.2)

    assert status == "completed"

    result = client.get(f"/api/research/jobs/{job_id}/result")
    assert result.status_code == 200
    data = result.json()["data"]
    assert "summary" in data
    assert len(data["key_findings"]) >= 1
