"""The /chat endpoint: one entry point, strategy chosen via `mode`."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from src.controllers.chat_controller import ChatController
from src.models.chat import ChatRequest

router = APIRouter()


def _controller(request: Request) -> ChatController:
    return request.app.state.controller


@router.post("/chat")
async def chat(payload: ChatRequest, request: Request) -> StreamingResponse:
    """Stream a recommendation reply token-by-token.

    `mode` selects the strategy (fewshot | rag | agent).
    """
    controller = _controller(request)
    try:
        controller.get(payload.mode)  # validate before we start streaming
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc

    return StreamingResponse(
        controller.stream(payload),
        media_type="text/plain; charset=utf-8",
    )
