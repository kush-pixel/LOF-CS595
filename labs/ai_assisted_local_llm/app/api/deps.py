"""FastAPI dependency injection helpers."""

from __future__ import annotations

from typing import AsyncGenerator

import asyncpg
import redis.asyncio as redis
from fastapi import Request


async def get_db_pool(request: Request) -> asyncpg.Pool:
    return request.app.state.db_pool


async def get_redis(request: Request) -> AsyncGenerator[redis.Redis, None]:
    r: redis.Redis = request.app.state.redis
    yield r
