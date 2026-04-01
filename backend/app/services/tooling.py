from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx

from app.core.config import settings


@dataclass
class ToolSpec:
    name: str
    description: str
    timeout_ms: int
    risk_level: str
    input_schema: dict
    output_schema: dict
    enabled: bool = True


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, ToolSpec] = {
            "amap_route_plan": ToolSpec(
                name="amap_route_plan",
                description="高德路线规划",
                timeout_ms=8000,
                risk_level="low",
                input_schema={
                    "type": "object",
                    "required": ["origin", "destination", "mode"],
                },
                output_schema={"type": "object"},
            ),
            "kb_search": ToolSpec(
                name="kb_search",
                description="Milvus知识库检索",
                timeout_ms=5000,
                risk_level="low",
                input_schema={"type": "object", "required": ["query"]},
                output_schema={"type": "object"},
            ),
        }

    def list_tools(self) -> list[ToolSpec]:
        return list(self._tools.values())

    def get(self, name: str) -> ToolSpec | None:
        return self._tools.get(name)


class ToolExecutor:
    def __init__(self, registry: ToolRegistry) -> None:
        self.registry = registry
        self._timeout = max(settings.tool_timeout_seconds, 1.0)

    async def execute(self, tool_name: str, arguments: dict) -> dict:
        spec = self.registry.get(tool_name)
        if not spec or not spec.enabled:
            raise ValueError("TOOL_NOT_ALLOWED")

        start = time.perf_counter()
        if tool_name == "amap_route_plan":
            result = await self._amap_route_plan(arguments)
        elif tool_name == "kb_search":
            result = await self._kb_search(arguments)
        else:
            raise ValueError("TOOL_NOT_ALLOWED")

        latency = int((time.perf_counter() - start) * 1000)
        return {
            "tool_call_id": f"tc_{uuid.uuid4().hex[:12]}",
            "tool_name": tool_name,
            "latency_ms": latency,
            "result": result,
        }

    async def _amap_route_plan(self, arguments: dict) -> dict:
        origin = arguments.get("origin", "")
        destination = arguments.get("destination", "")
        mode = arguments.get("mode", "driving")
        if not origin or not destination:
            raise ValueError("TOOL_BAD_ARGUMENTS")

        if not settings.amap_api_key:
            raise ValueError("AMAP_API_KEY_MISSING")

        origin_loc = await self._resolve_location(origin)
        destination_loc = await self._resolve_location(destination)
        endpoint, mode_key = self._route_endpoint(mode)

        params: dict[str, Any] = {
            "key": settings.amap_api_key,
            "origin": origin_loc,
            "destination": destination_loc,
            "output": "JSON",
        }
        if mode_key:
            params["strategy"] = mode_key

        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get(endpoint, params=params)
            payload = response.json()

        if str(payload.get("status")) != "1":
            raise ValueError("TOOL_UPSTREAM_ERROR")

        route = payload.get("route", {})
        paths = route.get("paths") or route.get("transits")
        if not paths:
            raise ValueError("MAP_ROUTE_NOT_FOUND")

        first = paths[0]
        steps = []
        if isinstance(first.get("steps"), list):
            steps = [item.get("instruction", "") for item in first["steps"] if item.get("instruction")]

        return {
            "distance_m": int(float(first.get("distance", 0))),
            "duration_s": int(float(first.get("duration", 0))),
            "steps": steps[:10],
            "source": "amap",
            "origin": origin_loc,
            "destination": destination_loc,
        }

    async def _kb_search(self, arguments: dict) -> dict:
        query = arguments.get("query", "")
        if not query:
            raise ValueError("TOOL_BAD_ARGUMENTS")
        if not settings.kb_search_endpoint:
            raise ValueError("KB_SEARCH_NOT_CONFIGURED")

        headers = {"Content-Type": "application/json"}
        if settings.kb_search_api_key:
            headers["Authorization"] = f"Bearer {settings.kb_search_api_key}"

        body = {"query": query, "top_k": arguments.get("top_k", 8), "filters": arguments.get("filters", {})}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(settings.kb_search_endpoint, headers=headers, json=body)
            payload = response.json()

        if response.status_code >= 400:
            raise ValueError("TOOL_UPSTREAM_ERROR")

        hits = payload.get("hits") or payload.get("data", {}).get("hits") or []
        return {"hits": hits}

    async def _resolve_location(self, text: str) -> str:
        if "," in text and len(text.split(",")) == 2:
            return text
        params = {"key": settings.amap_api_key, "address": text, "output": "JSON"}
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.get("https://restapi.amap.com/v3/geocode/geo", params=params)
            payload = response.json()
        if str(payload.get("status")) != "1":
            raise ValueError("TOOL_UPSTREAM_ERROR")
        geocodes = payload.get("geocodes", [])
        if not geocodes:
            raise ValueError("TOOL_BAD_ARGUMENTS")
        return geocodes[0]["location"]

    @staticmethod
    def _route_endpoint(mode: str) -> tuple[str, str | None]:
        if mode == "walking":
            return "https://restapi.amap.com/v5/direction/walking", None
        if mode == "cycling":
            return "https://restapi.amap.com/v4/direction/bicycling", None
        if mode == "transit":
            return "https://restapi.amap.com/v5/direction/transit/integrated", None
        return "https://restapi.amap.com/v5/direction/driving", "0"
