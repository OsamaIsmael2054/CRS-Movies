from typing import AsyncIterator

from src.routes.schemes.chat import ChatRequest
from src.strategies.base import RecommendationStrategy
from src.strategies.common import build_user_message
from src.strategies.fewShot.prompts import (
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
            {"role": "user", "content": build_user_message(watched, request.message)},
        ]
        async for chunk in self.llm.stream_chat(messages):
            yield chunk
