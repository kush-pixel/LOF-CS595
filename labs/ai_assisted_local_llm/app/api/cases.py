"""Cases API router — /api/v1/cases."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db_pool, get_redis
from app.db import queries
from app.schemas import (
    CaseCreateRequest,
    CaseGenerateRequest,
    CaseListResponse,
    CaseUpdateRequest,
    MedicalCase,
)
from app.services import cache_service, llm_service

router = APIRouter(prefix="/api/v1/cases", tags=["cases"])


def _row_to_case(row: dict) -> MedicalCase:
    data = row["case_data"]
    if isinstance(data, str):
        data = json.loads(data)
    data.update(
        case_id=str(row["case_id"]),
        case_number=row.get("case_number"),
        case_title=row["case_title"],
        specialty=row["specialty"],
        difficulty=row["difficulty"],
        created_at=row["created_at"].isoformat() if isinstance(row["created_at"], datetime) else row["created_at"],
        updated_at=row["updated_at"].isoformat() if isinstance(row["updated_at"], datetime) else row["updated_at"],
    )
    return MedicalCase.model_validate(data)


# ── Generate ───────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=MedicalCase)
async def generate_case(
    body: CaseGenerateRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    case = await llm_service.generate_case(
        specialty=body.specialty,
        prompt=body.prompt,
        difficulty=body.difficulty.value if body.difficulty else None,
        llm_provider=body.llm_provider,
        llm_model=body.llm_model,
    )
    diff = case.difficulty.value if hasattr(case.difficulty, "value") else case.difficulty
    case_dict = case.model_dump(mode="json")
    await queries.insert_case(
        pool,
        case_id=case.case_id,
        case_title=case.case_title,
        specialty=case.specialty,
        difficulty=diff,
        case_data=case_dict,
    )
    await cache_service.set_cached_case(r, case.case_id, case_dict)
    return case


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.post("/", response_model=MedicalCase, status_code=201)
async def create_case(
    body: CaseCreateRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    case_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)
    full_data = {
        **body.case_data,
        "case_id": case_id,
        "case_title": body.case_title,
        "specialty": body.specialty,
        "difficulty": body.difficulty.value,
        "created_at": now.isoformat(),
        "updated_at": now.isoformat(),
    }
    case = MedicalCase.model_validate(full_data)
    case_dict = case.model_dump(mode="json")
    await queries.insert_case(
        pool,
        case_id=case_id,
        case_title=body.case_title,
        specialty=body.specialty,
        difficulty=body.difficulty.value,
        case_data=case_dict,
    )
    await cache_service.set_cached_case(r, case_id, case_dict)
    return case


@router.get("/", response_model=CaseListResponse)
async def list_cases(
    page: int = 1,
    page_size: int = 20,
    specialty: str | None = None,
    search: str | None = None,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    rows, total = await queries.list_cases(
        pool, page=page, page_size=page_size, specialty=specialty, search=search,
    )
    items = [_row_to_case(r) for r in rows]
    return CaseListResponse(items=items, total=total, page=page, page_size=page_size)


@router.get("/by-number/{case_number}", response_model=MedicalCase)
async def get_case_by_number(
    case_number: int,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    row = await queries.get_case_by_number(pool, case_number)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    return _row_to_case(row)


@router.get("/{case_id}", response_model=MedicalCase)
async def get_case(
    case_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    cached = await cache_service.get_cached_case(r, case_id)
    if cached:
        return MedicalCase.model_validate(cached)

    row = await queries.get_case_by_id(pool, case_id)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    case = _row_to_case(row)
    await cache_service.set_cached_case(r, case_id, case.model_dump(mode="json"))
    return case


@router.put("/{case_id}", response_model=MedicalCase)
async def replace_case(
    case_id: str,
    body: CaseCreateRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    now = datetime.now(timezone.utc)
    full_data = {
        **body.case_data,
        "case_id": case_id,
        "case_title": body.case_title,
        "specialty": body.specialty,
        "difficulty": body.difficulty.value,
        "updated_at": now.isoformat(),
    }
    case = MedicalCase.model_validate(full_data)
    case_dict = case.model_dump(mode="json")
    row = await queries.update_case(
        pool,
        case_id,
        updates={
            "case_title": body.case_title,
            "specialty": body.specialty,
            "difficulty": body.difficulty.value,
            "case_data": case_dict,
        },
    )
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")
    await cache_service.set_cached_case(r, case_id, case_dict)
    return case


@router.patch("/{case_id}", response_model=MedicalCase)
async def patch_case(
    case_id: str,
    body: CaseUpdateRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    existing = await queries.get_case_by_id(pool, case_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Case not found")

    updates: dict = {}
    if body.case_title is not None:
        updates["case_title"] = body.case_title
    if body.specialty is not None:
        updates["specialty"] = body.specialty
    if body.difficulty is not None:
        updates["difficulty"] = body.difficulty.value

    if body.case_data is not None:
        current_data = existing["case_data"]
        if isinstance(current_data, str):
            current_data = json.loads(current_data)
        current_data.update(body.case_data)
        updates["case_data"] = current_data

    if not updates:
        return _row_to_case(existing)

    row = await queries.update_case(pool, case_id, updates=updates)
    if not row:
        raise HTTPException(status_code=404, detail="Case not found")

    case = _row_to_case(row)
    await cache_service.invalidate_case(r, case_id)
    return case


@router.delete("/{case_id}", status_code=204)
async def delete_case(
    case_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    deleted = await queries.delete_case(pool, case_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Case not found")
    await cache_service.invalidate_case(r, case_id)
