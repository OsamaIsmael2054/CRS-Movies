from typing import AsyncIterator

import asyncpg

from src.clients.ollama import OllamaClient
from src.routes.schemes.chat import ChatMode, ChatRequest
from src.strategies.agent.agent import AgentStrategy
from src.strategies.base import RecommendationStrategy
from src.strategies.fewShot.fewshot import FewShotStrategy
from src.strategies.rag.rag import RagStrategy
from src.stores.sessions import SessionStore


class ChatController:
    def __init__(
        self,
        llm: OllamaClient,
        pool: asyncpg.Pool,
        sessions: SessionStore | None = None,
    ) -> None:
        sessions = sessions or SessionStore()
        self.sessions = sessions
        self._strategies: dict[ChatMode, RecommendationStrategy] = {
            ChatMode.FEWSHOT: FewShotStrategy(llm, pool, sessions),
            ChatMode.RAG: RagStrategy(llm, pool, sessions),
            ChatMode.AGENT: AgentStrategy(llm, pool, sessions),
        }

    def get(self, mode: ChatMode) -> RecommendationStrategy:
        strategy = self._strategies.get(mode)
        if strategy is None:
            raise NotImplementedError(f"Mode '{mode.value}' is not implemented yet.")
        return strategy

    def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        return self.get(request.mode).stream(request)
