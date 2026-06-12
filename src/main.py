from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI

from src.clients.ollama import OllamaClient
from src.controllers.chat_controller import ChatController
from src.routes.chat import router as chat_router
from src.stores.database import create_pool


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    pool = await create_pool()
    llm = OllamaClient()
    app.state.pool = pool
    app.state.llm = llm
    app.state.controller = ChatController(llm=llm, pool=pool)
    try:
        yield
    finally:
        await llm.aclose()
        await pool.close()


app = FastAPI(title="Movies-CRS", lifespan=lifespan)
app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)