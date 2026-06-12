"""Approach 3 — Agent (LangChain).

Retrieval is dynamic and model-controlled: the LLM holds a CF-backed tool and
decides when to call it, iterating reason -> act -> observe. Built on LangChain's
``create_agent`` (the same shape as the retrieval agent it's modeled on) and
driven by ``ChatOllama``, so tool-calling and token streaming are handled
natively instead of by a hand-rolled loop.
"""

from __future__ import annotations

from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, HumanMessage
from langchain_ollama import ChatOllama

from src.routes.schemes.chat import ChatRequest
from src.strategies.agent.tools import (
    create_recommend_tool,
    create_search_tool,
    create_similar_tool,
    create_similar_users_tool,
)
from src.strategies.base import RecommendationStrategy
from src.strategies.agent.prompts import AGENT_SYSTEM_PROMPT
from src.strategies.common import build_user_message


class AgentStrategy(RecommendationStrategy):
    def _model(self) -> ChatOllama:
        """ChatOllama mirroring the project's Ollama client settings.

        ``reasoning`` is ChatOllama's switch for Ollama's ``think`` flag; gemma
        needs it off (it streams no content otherwise), which our client already
        encodes as ``think=False``.
        """
        think = self.llm.think
        return ChatOllama(
            model=self.llm.model,
            base_url=self.llm.base_url,
            temperature=self.llm.temperature,
            reasoning=think if isinstance(think, bool) else None,
        )

    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        watched = await self._titles(request.history)

        # Tools bind this request's pool + history, so the agent is per-request.
        agent = create_agent(
            model=self._model(),
            tools=[
                create_recommend_tool(self.pool, request),
                create_similar_users_tool(self.pool, request),
                create_search_tool(self.pool),
                create_similar_tool(self.pool),
            ],
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

        user_message = build_user_message(watched, request.message)
        async for token, _meta in agent.astream(
            {"messages": [HumanMessage(content=user_message)]},
            stream_mode="messages",
        ):
            # Tool-calling steps emit no text, so only final answer tokens stream.
            if isinstance(token, AIMessageChunk) and token.content:
                yield str(token.content)
