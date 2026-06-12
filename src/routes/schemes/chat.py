from enum import Enum

from pydantic import BaseModel, Field


class ChatMode(str, Enum):
    """Which CRS strategy handles the request."""

    FEWSHOT = "fewshot"
    RAG = "rag"
    AGENT = "agent"


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's latest message.")
    user_id: str = Field(
        ...,
        description="Known user id; their watch history is looked up server-side.",
    )
    mode: ChatMode = Field(
        default=ChatMode.FEWSHOT, description="Strategy used to answer."
    )
    session_id: str | None = Field(
        default=None,
        description=(
            "Conversation id. Prior turns for this session are looked up "
            "server-side and fed back to the model; omit for a stateless turn."
        ),
    )