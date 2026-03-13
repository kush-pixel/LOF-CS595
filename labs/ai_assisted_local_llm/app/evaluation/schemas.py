"""Pydantic models for the evaluation system."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


# ── Input Models ─────────────────────────────────────────────────────────────


class CaseDescription(BaseModel):
    """Structured case description for evaluation context."""

    demographics: dict = Field(default_factory=dict)
    chief_complaint: str = ""
    hpi: str = ""
    pmh: list[str] = Field(default_factory=list)
    medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    social_history: dict = Field(default_factory=dict)
    family_history: list[str] = Field(default_factory=list)
    ros: dict = Field(default_factory=dict)
    physical_exam_findings: dict = Field(default_factory=dict)
    labs: dict = Field(default_factory=dict)
    imaging: list[str] = Field(default_factory=list)
    differential_diagnosis: list[str] = Field(default_factory=list)
    final_diagnosis: str = ""
    emotional_presentation: str = ""


class TranscriptTurn(BaseModel):
    """A single turn in the student-patient conversation."""

    turn_number: int = Field(ge=1)
    speaker: Literal["Student", "Patient"]
    content: str


class Transcript(BaseModel):
    """Full conversation transcript with metadata."""

    turns: list[TranscriptTurn]
    session_id: str | None = None
    timestamp: datetime | None = None


# ── Output Models ────────────────────────────────────────────────────────────


class EvidenceCitation(BaseModel):
    """A reference to a specific transcript turn supporting a score."""

    turn_number: int = Field(description="Transcript turn number")
    speaker: Literal["Student", "Patient"]
    quote: str = Field(description="Relevant excerpt from that turn")
    relevance: str = Field(description="Why this supports the score")


class DimensionScore(BaseModel):
    """Score and rationale for a single evaluation dimension."""

    dimension: str
    score: int = Field(ge=1, le=5)
    weight: float
    evidence: list[EvidenceCitation]
    rationale: str = Field(description="CoT reasoning for this score")
    strengths: list[str]
    growth_areas: list[str]


class EvaluationResult(BaseModel):
    """Complete evaluation for one layer."""

    layer: Literal["case_fidelity", "student_performance"]
    dimensions: list[DimensionScore]
    weighted_total: float
    overall_summary: str
    top_recommendation: str


# ── Request / Response ───────────────────────────────────────────────────────


class EvaluationRequest(BaseModel):
    """Request to evaluate a transcript against a case."""

    case_description: CaseDescription
    transcript: Transcript
    layer: Literal["case_fidelity", "student_performance", "both"]
    rubric_version: str | None = None
    model: Literal["gpt-4o", "gemma3", "llama3.2"]


class EvaluationResponse(BaseModel):
    """Response containing evaluation results."""

    results: list[EvaluationResult]
    model_used: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    token_usage: dict = Field(default_factory=dict)
    evaluation_id: str | None = None
