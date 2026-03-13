"""Core evaluation engine — calls LLMs and parses structured results."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

import anthropic
import redis.asyncio as redis
import asyncio
from pydantic import BaseModel, Field

from app.config import settings
from app.evaluation.prompts import SYSTEM_PROMPT, build_evaluation_prompt
from app.evaluation.rubrics import get_rubric
from app.evaluation.schemas import (
    DimensionScore,
    EvaluationRequest,
    EvaluationResponse,
    EvaluationResult,
    EvidenceCitation,
)

logger = logging.getLogger(__name__)

EVAL_CACHE_TTL = 3600  # 1 hour


# ── Pydantic model for structured output ─────────────────────────────────
# Historically we relied on OpenAI's ``responses.parse`` API to validate
# against a Pydantic model.  The provider layer now abstracts over OpenAI or a
# local Ollama server; the comment below only applies when the real OpenAI
# client is in use, but the same schemas are enforced either way.
# OpenAI's responses.parse API takes a Pydantic model directly and handles
# the JSON schema generation (including additionalProperties: false).


class EvidenceCitationOutput(BaseModel):
    turn_number: int
    speaker: Literal["Student", "Patient"]
    quote: str
    relevance: str


class DimensionScoreOutput(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    weight: float
    evidence: list[EvidenceCitationOutput]
    rationale: str
    strengths: list[str]
    growth_areas: list[str]


class EvaluationOutput(BaseModel):
    """Top-level structured output for the evaluation response."""

    dimensions: list[DimensionScoreOutput]
    overall_summary: str
    top_recommendation: str


# ── Tool schema for Claude tool_use ──────────────────────────────────────────

EVALUATION_TOOL = {
    "name": "submit_evaluation",
    "description": "Submit the completed evaluation with scores for all dimensions.",
    "input_schema": {
        "type": "object",
        "properties": {
            "dimensions": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "dimension": {"type": "string"},
                        "score": {"type": "integer", "minimum": 1, "maximum": 5},
                        "weight": {"type": "number"},
                        "evidence": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "turn_number": {"type": "integer"},
                                    "speaker": {
                                        "type": "string",
                                        "enum": ["Student", "Patient"],
                                    },
                                    "quote": {"type": "string"},
                                    "relevance": {"type": "string"},
                                },
                                "required": [
                                    "turn_number",
                                    "speaker",
                                    "quote",
                                    "relevance",
                                ],
                            },
                        },
                        "rationale": {"type": "string"},
                        "strengths": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "growth_areas": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "dimension",
                        "score",
                        "weight",
                        "evidence",
                        "rationale",
                        "strengths",
                        "growth_areas",
                    ],
                },
            },
            "overall_summary": {"type": "string"},
            "top_recommendation": {"type": "string"},
        },
        "required": ["dimensions", "overall_summary", "top_recommendation"],
    },
}


def _cache_key(request: EvaluationRequest, layer: str) -> str:
    """Build a deterministic cache key from request contents."""
    transcript_text = "|".join(
        f"{t.turn_number}:{t.speaker}:{t.content}" for t in request.transcript.turns
    )
    raw = f"{request.case_description.model_dump_json()}|{transcript_text}|{layer}|{request.rubric_version or 'default'}"
    return f"eval:{hashlib.sha256(raw.encode()).hexdigest()}"


async def _get_cached(r: redis.Redis | None, key: str) -> dict | None:
    if r is None:
        return None
    try:
        raw = await r.get(key)
        if raw:
            return json.loads(raw)
    except Exception:
        logger.warning("Redis cache read failed", exc_info=True)
    return None


async def _set_cached(r: redis.Redis | None, key: str, data: dict) -> None:
    if r is None:
        return
    try:
        await r.set(key, json.dumps(data, default=str), ex=EVAL_CACHE_TTL)
    except Exception:
        logger.warning("Redis cache write failed", exc_info=True)


def _parse_tool_result(tool_input: dict, layer: str) -> EvaluationResult:
    """Parse a dict (from Claude tool_use or parsed Pydantic) into an EvaluationResult."""
    dimensions = []
    for dim in tool_input["dimensions"]:
        evidence = [EvidenceCitation(**e) for e in dim.get("evidence", [])]
        dimensions.append(
            DimensionScore(
                dimension=dim["dimension"],
                score=dim["score"],
                weight=dim["weight"],
                evidence=evidence,
                rationale=dim["rationale"],
                strengths=dim.get("strengths", []),
                growth_areas=dim.get("growth_areas", []),
            )
        )

    weighted_total = sum(d.score * d.weight for d in dimensions)

    return EvaluationResult(
        layer=layer,
        dimensions=dimensions,
        weighted_total=round(weighted_total, 2),
        overall_summary=tool_input["overall_summary"],
        top_recommendation=tool_input["top_recommendation"],
    )


async def _evaluate_with_claude(
    prompt: str, layer: str
) -> tuple[EvaluationResult, dict]:
    """Call Anthropic Claude with tool_use for structured output."""
    client = anthropic.AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)

    response = await client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        tools=[EVALUATION_TOOL],
        tool_choice={"type": "tool", "name": "submit_evaluation"},
        messages=[{"role": "user", "content": prompt}],
    )

    token_usage = {
        "input_tokens": response.usage.input_tokens,
        "output_tokens": response.usage.output_tokens,
    }

    # Extract tool_use block
    for block in response.content:
        if block.type == "tool_use" and block.name == "submit_evaluation":
            result = _parse_tool_result(block.input, layer)
            return result, token_usage

    raise ValueError("Claude did not return a tool_use response")


async def _evaluate_with_gpt4o(
    prompt: str, layer: str
) -> tuple[EvaluationResult, dict]:
    """Fallback: call OpenAI GPT-4o with responses.parse for structured output."""
    # Use the provider abstraction so we can target Ollama or OpenAI consistently.
    # We use the helper `_parse_with_schema` from the provider module which
    # attempts structured parsing and falls back to Pydantic validation.
    from app.services.llm_provider import provider, parse_with_schema

    # choose model depending on configured provider
    model = settings.OPENAI_MODEL
    if settings.LLM_PROVIDER.lower() == "ollama":
        model = settings.OLLAMA_MODEL

    client = provider().client

    # try parsing once (the helper already raises a clear error on mismatch)
    # retry parsing a few times for less-capable local models (e.g., Ollama)
    parsed = None
    last_exc: Exception | None = None
    attempts = 3 if settings.LLM_PROVIDER.lower() == "ollama" else 1
    for attempt in range(attempts):
        try:
            parsed = await parse_with_schema(
                client=client,
                model=model,
                messages=[{"role": "user", "content": prompt}],
                schema=EvaluationOutput,
            )
            break
        except Exception as exc:
            last_exc = exc
            # small backoff for retries
            if attempt < attempts - 1:
                await asyncio.sleep(1 + attempt)
                continue
            raise

    if parsed is None:
        raise ValueError("LLM returned empty parsed response for evaluation")

    # token usage is not available generically from the provider helper; return empty counts
    token_usage = {"input_tokens": 0, "output_tokens": 0}

    result = _parse_tool_result(parsed.model_dump(), layer)
    return result, token_usage


async def _evaluate_single_layer(
    request: EvaluationRequest,
    layer: str,
    r: redis.Redis | None = None,
) -> tuple[EvaluationResult, str, dict]:
    """Evaluate a single layer, with caching and fallback."""
    cache_key = _cache_key(request, layer)

    # Check cache
    cached = await _get_cached(r, cache_key)
    if cached:
        logger.info("Cache hit for %s", cache_key)
        result = EvaluationResult(**cached["result"])
        return result, cached["model_used"], cached.get("token_usage", {})

    rubric = get_rubric(layer)
    prompt = build_evaluation_prompt(
        request.case_description, request.transcript, rubric, layer
    )

    model_used = request.model
    token_usage: dict = {}

    if model_used == "llama3.2":
        try:
            result, token_usage = await _evaluate_with_ollama(prompt, layer, model_used)
            model_used = "llama3.2"
        except Exception:
            logger.warning("LLama evaluation failed, falling back to GPT-4o", exc_info=True)
            result, token_usage = await _evaluate_with_gpt4o(prompt, layer)
            model_used = "gpt-4o"
    elif model_used == "gemma3":
        try:
            result, token_usage = await _evaluate_with_ollama(prompt, layer, model_used)
            model_used = "gemma3"
        except Exception:
            logger.warning("Gemma evaluation failed, falling back to GPT-4o", exc_info=True)
            result, token_usage = await _evaluate_with_gpt4o(prompt, layer)
            model_used = "gpt-4o"
    else:
        result, token_usage = await _evaluate_with_gpt4o(prompt, layer)
        model_used = "gpt-4o"

    # Cache the result
    await _set_cached(
        r,
        cache_key,
        {
            "result": result.model_dump(mode="json"),
            "model_used": model_used,
            "token_usage": token_usage,
        },
    )

    return result, model_used, token_usage

async def _evaluate_with_ollama(
    prompt: str,
    layer: str,
    model: str | None = None,
) -> tuple[EvaluationResult, dict]:
    """Call Ollama via the provider abstraction and parse structured output."""
    from app.services.llm_provider import parse_with_schema, provider

    client = provider().client
    ollama_model = model or settings.OLLAMA_MODEL

    parsed = None
    last_exc: Exception | None = None

    for attempt in range(3):
        try:
            parsed = await parse_with_schema(
                client=client,
                model=ollama_model,
                messages=[{"role": "user", "content": prompt}],
                schema=EvaluationOutput,
            )
            break
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "Ollama evaluation parse failed for model=%s on attempt %s/%s",
                ollama_model,
                attempt + 1,
                3,
                exc_info=True,
            )
            if attempt < 2:
                await asyncio.sleep(1 + attempt)
            else:
                raise ValueError(
                    f"Ollama model '{ollama_model}' failed to return valid structured "
                    f"evaluation output: {exc}"
                ) from exc

    if parsed is None:
        raise ValueError(
            f"Ollama model '{ollama_model}' returned empty parsed response. "
            f"Last error: {last_exc}"
        )

    token_usage = {"input_tokens": 0, "output_tokens": 0}

    result = _parse_tool_result(parsed.model_dump(), layer)
    return result, token_usage

async def evaluate_transcript(
    request: EvaluationRequest,
    r: redis.Redis | None = None,
) -> EvaluationResponse:
    """Main entry point: evaluate a transcript against a case on one or both layers."""
    layers: list[str] = []
    if request.layer == "both":
        layers = ["case_fidelity", "student_performance"]
    else:
        layers = [request.layer]

    results: list[EvaluationResult] = []
    total_tokens: dict = {"input_tokens": 0, "output_tokens": 0}
    model_used = ""

    for layer in layers:
        result, used_model, tokens = await _evaluate_single_layer(request, layer, r)
        results.append(result)
        model_used = used_model
        total_tokens["input_tokens"] += tokens.get("input_tokens", 0)
        total_tokens["output_tokens"] += tokens.get("output_tokens", 0)

    return EvaluationResponse(
        results=results,
        model_used=model_used,
        timestamp=datetime.now(timezone.utc),
        token_usage=total_tokens,
        evaluation_id=str(uuid.uuid4()),
    )
