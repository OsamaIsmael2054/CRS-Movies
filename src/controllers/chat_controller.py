"""Selects and runs the CRS strategy for a chat request."""

from __future__ import annotations

from typing import AsyncIterator

import asyncpg

from src.clients.ollama import OllamaClient
from src.models.chat import ChatMode, ChatRequest
from src.strategies.agent.agent import AgentStrategy
from src.strategies.base import RecommendationStrategy
from src.strategies.fewShot.fewshot import FewShotStrategy
from src.strategies.rag.rag import RagStrategy


class ChatController:
    """Holds one instance of each strategy and dispatches by request mode."""

    def __init__(self, llm: OllamaClient, pool: asyncpg.Pool) -> None:
        self._strategies: dict[ChatMode, RecommendationStrategy] = {
            ChatMode.FEWSHOT: FewShotStrategy(llm, pool),
            ChatMode.RAG: RagStrategy(llm, pool),
            ChatMode.AGENT: AgentStrategy(llm, pool),
        }

    def get(self, mode: ChatMode) -> RecommendationStrategy:
        strategy = self._strategies.get(mode)
        if strategy is None:
            raise NotImplementedError(f"Mode '{mode.value}' is not implemented yet.")
        return strategy

    def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        return self.get(request.mode).stream(request)
