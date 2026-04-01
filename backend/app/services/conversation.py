from __future__ import annotations

import asyncio
import json
import uuid

from app.services.tooling import ToolExecutor


class ConversationEngine:
    def __init__(self, tool_executor: ToolExecutor):
        self.tool_executor = tool_executor

    async def stream_reply(self, user_text: str):
        request_id = f"req_{uuid.uuid4().hex[:12]}"
        message_id = f"msg_{uuid.uuid4().hex[:12]}"
        yield self._sse("message_start", {"request_id": request_id, "message_id": message_id})

        tool = self._decide_tool(user_text)
        context_note = ""
        if tool:
            yield self._sse("tool_call_start", {"tool_name": tool["name"], "args": tool["args"]})
            try:
                result = await self.tool_executor.execute(tool["name"], tool["args"])
                yield self._sse("tool_call_result", result)
                context_note = self._tool_to_text(result)
            except ValueError as exc:
                yield self._sse("tool_call_error", {"code": str(exc)})

        answer = self._compose_answer(user_text, context_note)
        for idx, chunk in enumerate(self._chunks(answer, size=12)):
            await asyncio.sleep(0.01)
            yield self._sse("message_delta", {"index": idx, "delta": chunk})

        yield self._sse("usage", {"prompt_tokens": 120, "completion_tokens": 210, "total_tokens": 330})
        yield self._sse("message_end", {"message_id": message_id, "finish_reason": "stop"})

    def _decide_tool(self, text: str) -> dict | None:
        lowered = text.lower()
        if any(k in text for k in ["路线", "导航", "怎么走"]) or "route" in lowered:
            return {
                "name": "amap_route_plan",
                "args": {"origin": "杭州东站", "destination": "西湖", "mode": "driving"},
            }
        if any(k in text for k in ["知识库", "文档", "检索"]):
            return {"name": "kb_search", "args": {"query": text}}
        return None

    def _compose_answer(self, user_text: str, context_note: str) -> str:
        base = f"已收到你的问题：{user_text}。"
        if context_note:
            base += f"\n\n工具结果：{context_note}"
        base += "\n\n这是v1实现，支持自动工具调用、SSE流式输出与异步研究任务。"
        return base

    def _tool_to_text(self, result: dict) -> str:
        payload = result.get("result", {})
        if "distance_m" in payload:
            return f"距离约{payload['distance_m']}米，耗时约{payload['duration_s']}秒。"
        if "hits" in payload:
            return f"命中{len(payload['hits'])}条知识片段。"
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _chunks(text: str, size: int):
        for i in range(0, len(text), size):
            yield text[i : i + size]

    @staticmethod
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
