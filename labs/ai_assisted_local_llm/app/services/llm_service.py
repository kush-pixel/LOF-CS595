"""OpenAI-powered medical case generation."""

from __future__ import annotations

import uuid

import openai

from app.config import settings
from app.schemas.medical_case import MedicalCase
from app.services.llm_provider import parse_with_schema

SYSTEM_PROMPT = (
    "You are a medical education case generator. Generate realistic, clinically accurate "
    "medical cases for computer science students learning about health informatics. "
    "Populate ALL fields with plausible clinical data. Return valid JSON matching the "
    "provided schema exactly. "
    "For case_id, always use a valid UUID v4 string (e.g. '550e8400-e29b-41d4-a716-446655440000')."
)


async def generate_case(
    *,
    specialty: str | None = None,
    prompt: str | None = None,
    difficulty: str | None = None,
    llm_provider: str | None = None,  # NEW: "openai" or "ollama"
    llm_model: str | None = None,     # NEW: model name (openai or ollama)
) -> MedicalCase:

    user_parts: list[str] = ["Generate a detailed medical case."]
    if specialty:
        user_parts.append(f"Specialty: {specialty}")
    if difficulty:
        user_parts.append(f"Difficulty: {difficulty}")
    if prompt:
        user_parts.append(f"Additional context: {prompt}")

    print(llm_provider)
    print(llm_model)

    # --- NEW: request-scoped provider/model selection ---
    provider_name = (llm_provider).lower()
    if provider_name == "ollama":
        base = settings.OLLAMA_API_BASE_URL or "http://localhost:11434/v1"
        client = openai.AsyncOpenAI(api_key="ollama", base_url=base)
        model = llm_model
    else:
        client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        model = llm_model
    # ----------------------------------------------------

    print(f"Using LLM provider: {provider_name}, model: {model}")

    case = await parse_with_schema(
        client=client,
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": " ".join(user_parts)},
        ],
        schema=MedicalCase,
    )

    case.case_id = str(uuid.uuid4())
    if specialty:
        case.specialty = specialty
    if difficulty:
        case.difficulty = difficulty  # type: ignore[assignment]
    return case

# async def generate_case(
#     *,
#     specialty: str | None = None,
#     prompt: str | None = None,
#     difficulty: str | None = None,
# ) -> MedicalCase:    

#     client_wrapper = provider()
#     client = client_wrapper.client

#     user_parts: list[str] = ["Generate a detailed medical case."]
#     if specialty:
#         user_parts.append(f"Specialty: {specialty}")
#     if difficulty:
#         user_parts.append(f"Difficulty: {difficulty}")
#     if prompt:
#         user_parts.append(f"Additional context: {prompt}")

#     # choose model according to provider
#     model = settings.OPENAI_MODEL
#     if client_wrapper.is_ollama:
#         model = settings.OLLAMA_MODEL

#     # parse response with schema validation and retries
#     case = await parse_with_schema(
#         client=client,
#         model=model,
#         messages=[
#             {"role": "system", "content": SYSTEM_PROMPT},
#             {"role": "user", "content": " ".join(user_parts)},
#         ],
#         schema=MedicalCase,
#     )

#     # ``_parse_with_schema`` either returns a MedicalCase instance or raises
#     # an error; we can trust ``case`` at this point.

#     # Override LLM-generated case_id with a proper UUID
#     case.case_id = str(uuid.uuid4())
#     if specialty:
#         case.specialty = specialty
#     if difficulty:
#         case.difficulty = difficulty  # type: ignore[assignment]
#     return case
