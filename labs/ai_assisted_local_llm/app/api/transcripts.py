"""Transcripts API router — save and retrieve interview transcripts."""

from __future__ import annotations

import asyncpg
from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_db_pool
from app.db.queries import insert_transcript, list_transcripts_by_case
from app.schemas import TranscriptSaveRequest, TranscriptSaveResponse

router = APIRouter(prefix="/api/v1/transcripts", tags=["transcripts"])


@router.post("/", response_model=TranscriptSaveResponse, status_code=201)
async def save_transcript(
    body: TranscriptSaveRequest,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    row = await insert_transcript(
        pool,
        conversation_id=body.conversation_id,
        case_number=body.case_number,
        transcript=body.transcript,
    )
    return TranscriptSaveResponse(
        conversation_id=str(row["conversation_id"]),
        case_number=row["case_number"],
        created_at=row["created_at"].isoformat(),
    )


@router.get("/by-case/{case_number}")
async def get_transcripts_by_case(
    case_number: int,
    pool: asyncpg.Pool = Depends(get_db_pool),
):
    rows = await list_transcripts_by_case(pool, case_number)
    if not rows:
        raise HTTPException(status_code=404, detail=f"No transcripts found for case #{case_number}")
    return [
        {
            "conversation_id": str(r["conversation_id"]),
            "case_number": r["case_number"],
            "transcript": r["transcript"],
            "created_at": r["created_at"].isoformat(),
        }
        for r in rows
    ]
