from typing import AsyncIterator

from src.routes.schemes.chat import ChatRequest
from src.stores.cf import recommend
from src.strategies.base import RecommendationStrategy
from src.strategies.rag.prompts import RAG_SYSTEM_PROMPT, build_rag_user_message


class RagStrategy(RecommendationStrategy):
    async def _candidates(self, request: ChatRequest) -> list[str]:
        """CF candidate titles for the request (popularity fallback on cold start)."""
        async with self.pool.acquire() as conn:
            candidates = await recommend(conn, history_ids=request.history)
        return [c.title for c in candidates]

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        watched = await self._titles(request.history)
        candidates = await self._candidates(request)

        messages = [
            {"role": "system", "content": RAG_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": build_rag_user_message(watched, candidates, request.message),
            },
        ]
        async for chunk in self.llm.stream_chat(messages):
            yield chunk
