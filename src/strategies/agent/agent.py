from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, HumanMessage

from clients.ollama import OllamaClient
from routes.schemes.chat import ChatRequest
from strategies.agent.tools import (
    create_recommend_tool,
    create_search_tool,
    create_similar_tool,
    create_similar_users_tool,
)
from strategies.base import RecommendationStrategy
from strategies.agent.prompts import AGENT_SYSTEM_PROMPT
from strategies.common import build_user_message


class AgentStrategy(RecommendationStrategy):
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        history = await self._history(request.user_id)
        watched = await self._titles(history)

        # Tools bind this request's pool + history, so the agent is per-request.
        agent = create_agent(
            model=self.llm.chat_model,
            tools=[
                create_recommend_tool(self.pool, history),
                create_similar_users_tool(self.pool, history),
                create_search_tool(self.pool),
                create_similar_tool(self.pool),
            ],
            system_prompt=AGENT_SYSTEM_PROMPT,
        )

        user_message = build_user_message(watched, request.message)
        prior_turns = OllamaClient._to_messages(self._turns(request.session_id))
        messages = [*prior_turns, HumanMessage(content=user_message)]

        parts: list[str] = []
        async for token, _meta in agent.astream(
            {"messages": messages},
            stream_mode="messages",
        ):
            # Tool-calling steps emit no text, so only final answer tokens stream.
            if isinstance(token, AIMessageChunk) and token.content:
                parts.append(str(token.content))
                yield str(token.content)
        self._remember(request.session_id, request.message, "".join(parts))
