from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.db import init_db
from app.routers import action_points, approval, transcribe


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    init_db()
    yield


app = FastAPI(
    title="Voice-to-Action-Points Assistant",
    description="Speak an instruction, get a structured Action Point, approve it, and only then does the system act.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(transcribe.router)
app.include_router(action_points.router)
app.include_router(approval.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
