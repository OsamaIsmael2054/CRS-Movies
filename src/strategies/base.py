from abc import ABC, abstractmethod
from typing import AsyncIterator

import asyncpg

from clients.ollama import OllamaClient
from routes.schemes.chat import ChatRequest
from stores.sessions import SessionStore, Turn


class RecommendationStrategy(ABC):
    """A recommendation strategy that streams a response token-by-token.

    Strategies share the Ollama client, the asyncpg pool, and the conversation
    session store; each one differs only in how it builds context and
    orchestrates the LLM call(s).
    """

    def __init__(
        self, llm: OllamaClient, pool: asyncpg.Pool, sessions: SessionStore
    ) -> None:
        self.llm = llm
        self.pool = pool
        self.sessions = sessions

    @abstractmethod
    def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        """Yield response text chunks for the given request."""
        ...

    def _turns(self, session_id: str | None) -> list[Turn]:
        """Prior conversation turns for this session (empty if stateless)."""
        return self.sessions.get(session_id)

    def _remember(
        self, session_id: str | None, user_message: str, reply: str
    ) -> None:
        """Persist this exchange so the next turn in the session sees it."""
        self.sessions.append(session_id, user_message, reply)

    async def _history(self, user_id: str | None) -> list[str]:
        """Fetch the item ids this user has watched, from the interaction matrix.

        Unknown / missing users yield an empty history (cold start), which the
        CF layer handles via its popularity fallback.
        """
        if not user_id:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT item_id FROM interactions WHERE user_id = $1", user_id
            )
        return [r["item_id"] for r in rows]

    async def _titles(self, item_ids: list[str]) -> list[str]:
        """Resolve catalog item ids to titles, preserving input order."""
        if not item_ids:
            return []
        async with self.pool.acquire() as conn:
            rows = await conn.fetch(
                "SELECT item_id, title FROM items WHERE item_id = ANY($1::text[])",
                item_ids,
            )
        by_id = {r["item_id"]: r["title"] for r in rows}
        return [by_id[i] for i in item_ids if i in by_id]
