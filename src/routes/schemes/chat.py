class ChatMode(str, Enum):
    """Which CRS strategy handles the request."""

    FEWSHOT = "fewshot"
    RAG = "rag"
    AGENT = "agent"


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's latest message.")
    history: list[str] = Field(
        default_factory=list,
        description="Item ids the user has already watched (catalog ids).",
    )
    user_id: str | None = Field(
        default=None, description="Optional known user id for personalization."
    )
    mode: ChatMode = Field(
        default=ChatMode.FEWSHOT, description="Strategy used to answer."
    )