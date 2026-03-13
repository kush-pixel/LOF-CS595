# Architecture Guide — Medical Case Generator

This document explains the system design for CS students learning about health informatics and full-stack AI applications.

---

## System Overview

```
┌──────────────┐     HTTP/JSON     ┌──────────────────┐     SQL      ┌────────────┐
│   Streamlit  │ ◄──────────────►  │  FastAPI Backend  │ ◄──────────► │ PostgreSQL │
│   Frontend   │                   │  (async, uvicorn) │              │  (JSONB)   │
└──────────────┘                   └────────┬─────────┘              └────────────┘
                                            │
                                   ┌────────┴─────────┐
                                   │                   │
                              ┌────▼─────┐      ┌─────▼────┐
                              │  LLM     │      │  Redis   │
                              │  Provider│      │  Cache   │
                              │  (OpenAI / Ollama)
                              └──────────┘      └──────────┘
```

**Components:**

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Frontend | Streamlit | Interactive UI for generating, browsing, and editing cases |
| Backend | FastAPI + Uvicorn | Async REST API with Pydantic validation |
| Database | PostgreSQL + asyncpg | Persistent JSONB storage with denormalized columns |
| Cache | Redis | Read-through cache with 1-hour TTL |
| LLM | OpenAI GPT-4o <br>or a local Ollama model | Structured output generation of medical cases (configurable via LLM_PROVIDER, default is OpenAI; see `app/services/llm_provider.py` for provider pattern) |

---

## Request Flow Walkthrough

### Generate a Case (happy path)

1. **User** clicks "Generate" in Streamlit → `POST /api/v1/cases/generate`
2. **FastAPI** validates the `CaseGenerateRequest` body (specialty, prompt, difficulty)
3. **LLM Service** uses the provider layer which will instantiate either an OpenAI client or an Ollama-compatible
   client (controlled by the ``LLM_PROVIDER`` environment variable).  The call is conceptually the same –
   ``responses.parse`` with ``response_format=MedicalCase`` – but the provider adds validation and retry logic for
   local models.
4. **Pydantic** validates the LLM output at the boundary (field ranges, enums, UUID format)
5. **DB Layer** inserts a row into `cases` — the full case is stored as JSONB, with denormalized columns for `specialty`, `difficulty`, and `case_title`
6. **Cache** stores the case in Redis (`case:{id}` → JSON, TTL 1h)
7. **Response** returns the validated `MedicalCase` to the frontend
8. **Streamlit** renders the case in collapsible expanders

### Read a Case (cache-first)

1. **Redis** is checked first → cache hit returns immediately
2. On cache miss → **PostgreSQL** query → result cached → returned

---

## Data Model Hierarchy

The root `MedicalCase` model contains ~30 nested Pydantic models organized into clinical sections:

```
MedicalCase (root)
├── PatientDemographics
├── VitalSigns (validated ranges: HR 0–300, SpO2 0–100, GCS 3–15, etc.)
├── ChiefComplaintHPI
├── ReviewOfSystems → list[SystemReview]
├── PastMedicalHistory
├── PastSurgicalHistory
├── FamilyHistory → list[FamilyMember]
├── SocialHistory
├── list[Medication]
├── list[Allergy]
├── PhysicalExam
│   ├── HEENTExam
│   ├── CardiovascularExam
│   ├── PulmonaryExam
│   ├── AbdominalExam
│   ├── NeurologicalExam
│   ├── MusculoskeletalExam
│   ├── SkinExam
│   └── PsychiatricExam
├── Diagnostics
│   ├── LabResults (CBC, BMP, HepaticPanel, Coagulation, Urinalysis, CardiacMarkers, MiscLab)
│   ├── list[ImagingStudy]
│   └── other_studies
├── Assessment (differential diagnoses, working/final diagnosis, clinical reasoning)
└── Plan (management steps, disposition, follow-up, patient education)
```

All lab values are `float | None` — `None` means "not ordered." This avoids sentinel values (like `-1`) that could be confused with real results.

---

## Why JSONB Over Normalized Tables

A fully normalized schema for this data model would require 20+ tables with complex foreign keys. We chose JSONB because:

1. **Schema flexibility** — The LLM may produce varying structures. JSONB tolerates this without migrations.
2. **Read performance** — A single row fetch returns the entire case. No JOINs needed.
3. **Pydantic validates at the app layer** — We don't rely on the DB for structural validation. The Pydantic models are the source of truth.
4. **GIN indexing** — PostgreSQL GIN indexes on JSONB support fast `@>` containment queries when needed.
5. **Denormalized columns** — `specialty`, `difficulty`, and `case_title` are stored as regular columns for efficient filtering and indexing without JSONB operators.

**Trade-off:** Cross-case analytics (e.g., "find all cases with potassium > 5.5") are harder with JSONB. For this educational project, that's acceptable.

---

## Why Raw SQL Over an ORM

1. **Transparency** — Students can see exactly what SQL executes. No magic.
2. **asyncpg performance** — asyncpg is the fastest Python PostgreSQL driver. ORMs add overhead.
3. **JSONB control** — ORMs don't always handle JSONB well. Raw SQL gives full control over `::jsonb` casts and GIN index usage.
4. **Fewer dependencies** — No SQLAlchemy/Alembic to learn or configure.

---

## Caching Strategy

- **Pattern:** Read-through cache with explicit invalidation
- **Key format:** `case:{uuid}`
- **TTL:** 1 hour (configurable in `cache_service.py`)
- **Invalidation:** On `PATCH`, `PUT`, and `DELETE` the cache entry is deleted
- **Cache miss:** DB query → cache write → return

This keeps the cache simple. For a production system, you'd add cache warming, TTL tuning, and possibly a write-through pattern.

---

## Error Handling

| Layer | Strategy |
|-------|----------|
| Pydantic schemas | `field_validator` with range checks; invalid data raises `ValidationError` |
| LLM service | Checks for `message.refusal` and empty responses; raises `ValueError` |
| API routes | Returns 404 for missing cases, 422 for validation errors (automatic via FastAPI) |
| Database | Connection pool with min/max sizing; pool exhaustion raises `RuntimeError` |

---

## How to Extend the Schema

1. **Add a new field** — Add the field to the appropriate Pydantic model in `app/schemas/medical_case.py`. Use `| None = None` for optional fields. No DB migration needed (it's JSONB).

2. **Add a new exam section** — Create a new `BaseModel` subclass, add it to `PhysicalExam`, and the LLM will populate it on next generation.

3. **Add a new lab panel** — Create a `BaseModel` in the Diagnostics section, add it to `LabResults`. Existing cases without the new panel will simply have `None`.

4. **Add a new API endpoint** — Add a route to `app/api/cases.py`. Follow the existing pattern of dependency injection via `Depends(get_db_pool)` and `Depends(get_redis)`.

5. **Add specialty-specific fields** — Create a new model and add it as an optional field on `MedicalCase`. The JSONB storage handles this without schema changes.
