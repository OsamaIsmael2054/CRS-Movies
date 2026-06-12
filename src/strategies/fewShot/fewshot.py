"""Approach 1 — Few-shot baseline.

No retrieval of candidates: the model recommends from its parametric memory,
primed with one fixed dataset conversation as a few-shot demonstration plus the
user's watched titles. A single streaming LLM call. This establishes the floor
that the CF-grounded approaches are measured against.

(The DB is touched only to resolve the user's history ids to titles — not to
retrieve recommendations.)
"""

from __future__ import annotations

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
        watched = await self._titles(request.history)

        system = f"{SYSTEM_PROMPT}\n\n{FEWSHOT_BLOCK.format(example=FEWSHOT_EXAMPLE)}"

        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": build_user_message(watched, request.message)},
        ]
        async for chunk in self.llm.stream_chat(messages):
            yield chunk
