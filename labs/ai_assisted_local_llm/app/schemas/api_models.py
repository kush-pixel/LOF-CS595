"""API request and response models."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.medical_case import Difficulty, MedicalCase


class CaseGenerateRequest(BaseModel):
    specialty: str | None = None
    prompt: str | None = None
    difficulty: Difficulty | None = None
    llm_provider: str | None = None  # "openai" or "ollama"
    llm_model: str | None = None     # e.g., "llama3


class CaseCreateRequest(BaseModel):
    """Full MedicalCase payload without server-managed fields (id/timestamps)."""

    case_title: str = ""
    specialty: str = "general"
    difficulty: Difficulty = Difficulty.MEDIUM
    # Remaining fields mirror MedicalCase but are passed as raw dict
    # and merged at the service layer.
    case_data: dict


class CaseUpdateRequest(BaseModel):
    """Partial update — all fields optional."""

    case_title: str | None = None
    specialty: str | None = None
    difficulty: Difficulty | None = None
    case_data: dict | None = None


class CaseListResponse(BaseModel):
    items: list[MedicalCase]
    total: int
    page: int = Field(..., ge=1)
    page_size: int = Field(..., ge=1)


# ── Transcript models ────────────────────────────────────────────────────────


class TranscriptSaveRequest(BaseModel):
    conversation_id: str
    case_number: int
    transcript: list[dict]


class TranscriptSaveResponse(BaseModel):
    conversation_id: str
    case_number: int
    created_at: str
