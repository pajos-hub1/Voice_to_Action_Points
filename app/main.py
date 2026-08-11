import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import init_db
from app.middleware import log_request_latency
from app.routers import action_points, approval, audit, execute, transcribe

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


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

app.middleware("http")(log_request_latency)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transcribe.router)
app.include_router(action_points.router)
app.include_router(approval.router)
app.include_router(execute.router)
app.include_router(audit.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
