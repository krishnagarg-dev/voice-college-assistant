import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config.settings import settings
from app.rag.bootstrap import ensure_knowledge_index
from app.routes import chat, health


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        ensure_knowledge_index()
    except Exception:
        # A temporary source/model/network failure must not take health and
        # tool endpoints offline. RAG returns its existing no-context answer.
        logger.exception("KIET knowledge index initialization failed; starting API without seeded RAG data")
    yield


app = FastAPI(
    title="KIET College Information Assistant API",
    description="API for the KIET Deemed to be University voice assistant.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(health.router)
app.include_router(chat.router)
