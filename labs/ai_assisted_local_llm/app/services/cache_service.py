"""Redis read-through cache for medical cases."""

from __future__ import annotations

import json

import redis.asyncio as redis

CASE_TTL_SECONDS = 3600  # 1 hour


async def get_cached_case(r: redis.Redis, case_id: str) -> dict | None:
    raw = await r.get(f"case:{case_id}")
    if raw is None:
        return None
    return json.loads(raw)


async def set_cached_case(r: redis.Redis, case_id: str, data: dict) -> None:
    await r.set(f"case:{case_id}", json.dumps(data, default=str), ex=CASE_TTL_SECONDS)


async def invalidate_case(r: redis.Redis, case_id: str) -> None:
    await r.delete(f"case:{case_id}")
