from __future__ import annotations

import asyncio
import time
import uuid
from dataclasses import dataclass


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
        await asyncio.sleep(0.05)
        origin = arguments.get("origin", "")
        destination = arguments.get("destination", "")
        mode = arguments.get("mode", "driving")
        if not origin or not destination:
            raise ValueError("TOOL_BAD_ARGUMENTS")

        return {
            "distance_m": 8900,
            "duration_s": 1320,
            "steps": [
                f"从 {origin} 出发",
                f"按 {mode} 推荐路线前往 {destination}",
                "到达目的地",
            ],
            "source": "amap",
        }

    async def _kb_search(self, arguments: dict) -> dict:
        await asyncio.sleep(0.03)
        query = arguments.get("query", "")
        if not query:
            raise ValueError("TOOL_BAD_ARGUMENTS")
        return {
            "hits": [
                {
                    "doc_id": "doc_demo",
                    "chunk_id": "chunk_001",
                    "score": 0.87,
                    "snippet": f"与“{query}”相关的知识片段。",
                }
            ]
        }
