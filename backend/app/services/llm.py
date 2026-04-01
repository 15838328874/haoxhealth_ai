from __future__ import annotations

import asyncio
import json

import httpx

from app.core.config import settings


class DashScopeError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


class DashScopeClient:
    def __init__(self) -> None:
        self.base_url = settings.dashscope_base_url.rstrip("/")
        self.timeout = settings.dashscope_timeout_seconds
        self.max_retries = max(settings.dashscope_max_retries, 0)

    async def stream_chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float,
        max_tokens: int,
    ):
        if not settings.dashscope_api_key:
            fallback = "未配置 DASHSCOPE_API_KEY，当前返回本地降级响应。"
            for chunk in self._chunks(fallback, 12):
                yield chunk
            return

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
        }
        headers = {
            "Authorization": f"Bearer {settings.dashscope_api_key}",
            "Content-Type": "application/json",
        }

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    async with client.stream(
                        "POST",
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    ) as response:
                        if response.status_code >= 400:
                            text = await response.aread()
                            raise DashScopeError("DASHSCOPE_HTTP_ERROR", text.decode("utf-8", errors="ignore"))

                        async for line in response.aiter_lines():
                            if not line or not line.startswith("data:"):
                                continue
                            data = line.replace("data:", "", 1).strip()
                            if data == "[DONE]":
                                return
                            try:
                                item = json.loads(data)
                            except json.JSONDecodeError:
                                continue
                            delta = (
                                item.get("choices", [{}])[0]
                                .get("delta", {})
                                .get("content")
                            )
                            if delta:
                                yield delta
                        return
            except (httpx.TimeoutException, httpx.TransportError, DashScopeError) as exc:
                if attempt >= self.max_retries:
                    code = exc.code if isinstance(exc, DashScopeError) else "DASHSCOPE_TIMEOUT_OR_NETWORK"
                    raise DashScopeError(code, str(exc)) from exc
                await asyncio.sleep(0.2 * (attempt + 1))

    @staticmethod
    def _chunks(text: str, size: int):
        for i in range(0, len(text), size):
            yield text[i : i + size]
