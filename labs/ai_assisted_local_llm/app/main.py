"""FastAPI application entry point."""

from __future__ import annotations

from contextlib import asynccontextmanager

import redis.asyncio as redis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.cases import router as cases_router
from app.api.transcripts import router as transcripts_router
from app.evaluation.router import router as evaluation_router
from app.config import settings
from app.db.connection import close_pool, create_pool
from app.db.queries import init_schema


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    pool = await create_pool()
    await init_schema(pool)
    app.state.db_pool = pool
    app.state.redis = redis.from_url(settings.REDIS_URL, decode_responses=True)
    yield
    # Shutdown
    await app.state.redis.aclose()
    await close_pool()


app = FastAPI(
    title="Medical Case Generator",
    description="AI-assisted medical case generation for CS students",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(cases_router)
app.include_router(transcripts_router)
app.include_router(evaluation_router)
