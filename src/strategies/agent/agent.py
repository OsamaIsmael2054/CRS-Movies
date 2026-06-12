from typing import AsyncIterator

from langchain.agents import create_agent
from langchain_core.messages import AIMessageChunk, HumanMessage

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
    async def stream(self, request: ChatRequest) -> AsyncIterator[str]:
        watched = await self._titles(request.history)

        # Tools bind this request's pool + history, so the agent is per-request.
        agent = create_agent(
            model=self.llm.chat_model,
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
