from typing import AsyncIterator

from routes.schemes.chat import ChatRequest
from strategies.base import RecommendationStrategy
from strategies.common import build_user_message
from strategies.fewShot.prompts import (
    FEWSHOT_BLOCK,
    FEWSHOT_EXAMPLE,
    SYSTEM_PROMPT,
)


class FewShotStrategy(RecommendationStrategy):
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        history = await self._history(request.user_id)
        watched = await self._titles(history)

        system = f"{SYSTEM_PROMPT}\n\n{FEWSHOT_BLOCK.format(example=FEWSHOT_EXAMPLE)}"

        messages = [
            {"role": "system", "content": system},
            *self._turns(request.session_id),
            {"role": "user", "content": build_user_message(watched, request.message)},
        ]
        parts: list[str] = []
        async for chunk in self.llm.stream_chat(messages):
            parts.append(chunk)
            yield chunk
        self._remember(request.session_id, request.message, "".join(parts))
