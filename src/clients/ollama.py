import json
from typing import Any, AsyncIterator

import httpx

from src.helpers.config import settings


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float | None = None,
        temperature: float | None = None,
        think: bool | str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.temperature = (
            temperature if temperature is not None else settings.ollama_temperature
        )
        self.think = think if think is not None else settings.ollama_think
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout or settings.ollama_timeout,
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "OllamaClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    def _options(self, overrides: dict[str, Any] | None) -> dict[str, Any]:
        options = {"temperature": self.temperature}
        if overrides:
            options.update(overrides)
        return options

    async def stream_generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "prompt": prompt,
            "stream": True,
            "think": self.think,
            "options": self._options(options),
        }
        if system:
            payload["system"] = system
        async for chunk in self._stream("/api/generate", payload, key="response"):
            yield chunk

    async def stream_chat(
        self,
        messages: list[dict[str, Any]],
        *,
        options: dict[str, Any] | None = None,
    ) -> AsyncIterator[str]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "think": self.think,
            "options": self._options(options),
        }
        async for chunk in self._stream("/api/chat", payload, key="message"):
            yield chunk

    async def chat(
        self,
        messages: list[dict[str, Any]],
        *,
        tools: list[dict[str, Any]] | None = None,
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "think": self.think,
            "options": self._options(options),
        }
        if tools:
            payload["tools"] = tools
        resp = await self._client.post("/api/chat", json=payload)
        resp.raise_for_status()
        return resp.json().get("message", {})

    async def _stream(
        self, path: str, payload: dict[str, Any], *, key: str
    ) -> AsyncIterator[str]:
        async with self._client.stream("POST", path, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                data = json.loads(line)
                if "error" in data:
                    raise RuntimeError(f"Ollama error: {data['error']}")
                if key == "message":
                    chunk = (data.get("message") or {}).get("content", "")
                else:
                    chunk = data.get(key, "")
                if chunk:
                    yield chunk
                if data.get("done"):
                    break
