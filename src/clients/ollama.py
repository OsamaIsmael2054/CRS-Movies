from typing import AsyncIterator

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
)
from langchain_ollama import ChatOllama

from helpers.config import settings

_ROLE_TO_MESSAGE: dict[str, type[BaseMessage]] = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}


class OllamaClient:
    def __init__(
        self,
        *,
        base_url: str | None = None,
        model: str | None = None,
        temperature: float | None = None,
        think: bool | str | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ollama_base_url).rstrip("/")
        self.model = model or settings.ollama_model
        self.temperature = (
            temperature if temperature is not None else settings.ollama_temperature
        )
        self.think = think if think is not None else settings.ollama_think
        # ChatOllama's ``reasoning`` flag maps to Ollama's ``think``; gemma needs
        # it off (it streams no content otherwise), which our default encodes as
        # ``think=False``. A non-bool ``think`` leaves the model default in place.
        self._chat = ChatOllama(
            model=self.model,
            base_url=self.base_url,
            temperature=self.temperature,
            reasoning=self.think if isinstance(self.think, bool) else None,
        )

    @property
    def chat_model(self) -> ChatOllama:
        """The underlying ChatOllama, for callers that need it (e.g. the agent)."""
        return self._chat

    @staticmethod
    def _to_messages(messages: list[dict[str, str]]) -> list[BaseMessage]:
        """Convert role/content dicts into LangChain message objects."""
        return [
            _ROLE_TO_MESSAGE.get(m["role"], HumanMessage)(content=m["content"])
            for m in messages
        ]

    async def stream_chat(
        self, messages: list[dict[str, str]]
    ) -> AsyncIterator[str]:
        """Stream a chat completion token-by-token as plain text."""
        async for chunk in self._chat.astream(self._to_messages(messages)):
            if chunk.content:
                yield str(chunk.content)
