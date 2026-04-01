from __future__ import annotations

import json
import uuid

from app.services.llm import DashScopeClient, DashScopeError
from app.services.tooling import ToolExecutor


class ConversationEngine:
    def __init__(self, tool_executor: ToolExecutor, llm_client: DashScopeClient):
        self.tool_executor = tool_executor
        self.llm_client = llm_client

    async def stream_reply(self, user_text: str, *, model: str, temperature: float, max_tokens: int):
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

        messages = self._build_messages(user_text, context_note)
        idx = 0
        try:
            async for chunk in self.llm_client.stream_chat(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            ):
                yield self._sse("message_delta", {"index": idx, "delta": chunk})
                idx += 1
        except DashScopeError as exc:
            yield self._sse("error", {"code": exc.code, "message": str(exc)})

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

    def _build_messages(self, user_text: str, context_note: str) -> list[dict[str, str]]:
        system_prompt = "你是一个专业、简洁的中文AI助手。"
        if context_note:
            system_prompt += f" 你可以参考以下工具结果：{context_note}"
        return [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text},
        ]

    def _tool_to_text(self, result: dict) -> str:
        payload = result.get("result", {})
        if "distance_m" in payload:
            return f"距离约{payload['distance_m']}米，耗时约{payload['duration_s']}秒。"
        if "hits" in payload:
            return f"命中{len(payload['hits'])}条知识片段。"
        return json.dumps(payload, ensure_ascii=False)

    @staticmethod
    def _sse(event: str, data: dict) -> str:
        return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
