"""Evaluation API router — /api/v1/evaluate."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

import asyncpg
import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db_pool, get_redis
from app.evaluation.engine import evaluate_transcript
from app.evaluation.rubrics import CASE_FIDELITY_RUBRIC, STUDENT_PERFORMANCE_RUBRIC
from app.evaluation.schemas import EvaluationRequest, EvaluationResponse

router = APIRouter(prefix="/api/v1/evaluate", tags=["evaluation"])


# ── Evaluate ─────────────────────────────────────────────────────────────────


@router.post("/", response_model=EvaluationResponse)
async def run_evaluation(
    body: EvaluationRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    response = await evaluate_transcript(body, r=r)

    # Persist to database
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO evaluations (evaluation_id, session_id, layer, result, model_used, token_usage, created_at)
            VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7)
            """,
            uuid.UUID(response.evaluation_id),
            body.transcript.session_id or "anonymous",
            body.layer,
            json.dumps([r.model_dump(mode="json") for r in response.results]),
            body.model,
            json.dumps(response.token_usage),
            datetime.now(timezone.utc),
        )

    return response


@router.post("/batch", response_model=list[EvaluationResponse])
async def run_batch_evaluation(
    bodies: list[EvaluationRequest],
    pool: asyncpg.Pool = Depends(get_db_pool),
    r: redis.Redis = Depends(get_redis),
):
    """Evaluate multiple transcripts against the same or different cases."""
    results = []
    for body in bodies:
        response = await evaluate_transcript(body, r=r)

        async with pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO evaluations (evaluation_id, session_id, layer, result, model_used, token_usage, created_at)
                VALUES ($1, $2, $3, $4::jsonb, $5, $6::jsonb, $7)
                """,
                uuid.UUID(response.evaluation_id),
                body.transcript.session_id or "anonymous",
                body.layer,
                json.dumps([r.model_dump(mode="json") for r in response.results]),
                response.model_used,
                json.dumps(response.token_usage),
                datetime.now(timezone.utc),
            )

        results.append(response)
    return results


@router.get("/{evaluation_id}", response_model=EvaluationResponse)
async def get_evaluation(
    evaluation_id: str,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    """Retrieve a stored evaluation by ID."""
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            "SELECT * FROM evaluations WHERE evaluation_id = $1",
            uuid.UUID(evaluation_id),
        )
    if not row:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    result_data = row["result"]
    if isinstance(result_data, str):
        result_data = json.loads(result_data)

    token_usage = row["token_usage"]
    if isinstance(token_usage, str):
        token_usage = json.loads(token_usage)

    return EvaluationResponse(
        results=result_data,
        model_used=row["model_used"],
        timestamp=row["created_at"],
        token_usage=token_usage,
        evaluation_id=str(row["evaluation_id"]),
    )


# ── Rubrics ──────────────────────────────────────────────────────────────────


@router.get("/rubrics/list")
async def list_rubrics():
    """List available rubric definitions."""
    return {
        "rubrics": [
            {
                "name": CASE_FIDELITY_RUBRIC["name"],
                "layer": CASE_FIDELITY_RUBRIC["layer"],
                "version": CASE_FIDELITY_RUBRIC["version"],
                "dimension_count": len(CASE_FIDELITY_RUBRIC["dimensions"]),
            },
            {
                "name": STUDENT_PERFORMANCE_RUBRIC["name"],
                "layer": STUDENT_PERFORMANCE_RUBRIC["layer"],
                "version": STUDENT_PERFORMANCE_RUBRIC["version"],
                "dimension_count": len(STUDENT_PERFORMANCE_RUBRIC["dimensions"]),
            },
        ]
    }


@router.get("/rubrics/{layer}")
async def get_rubric_detail(layer: str):
    """Get full rubric definition for a layer."""
    if layer == "case_fidelity":
        return CASE_FIDELITY_RUBRIC
    if layer == "student_performance":
        return STUDENT_PERFORMANCE_RUBRIC
    raise HTTPException(status_code=404, detail=f"Unknown layer: {layer}")
