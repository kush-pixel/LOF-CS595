# Session 2: Evaluation Layers — Plans, Prompts & Architecture

## Overview

Session 2 builds the **evaluation layer** on top of the Session 1 simulated patient infrastructure. The core deliverable is a Streamlit-based app that accepts (1) a structured case description and (2) a student–patient conversation transcript, then produces scored evaluations across two orthogonal axes:

- **Layer 1 — Case Fidelity**: Does the LLM-simulated patient faithfully represent the case?
- **Layer 2 — Student Performance**: Does the student demonstrate sound diagnostic reasoning and empathic communication?

---

## Architecture Summary

```
┌─────────────────┐     ┌──────────────────────┐     ┌─────────────────────┐
│     INPUTS       │     │   EVALUATION ENGINE   │     │      OUTPUTS         │
│                  │     │                        │     │                      │
│  Case JSON       │────▶│  Prompt Assembly       │────▶│  Dimension Scores    │
│  Transcript      │     │  LLM-as-Judge (Claude) │     │  CoT Rationale       │
│  Rubric Config   │     │  Structured Output      │     │  Evidence Citations  │
│                  │     │  (tool_use / JSON mode) │     │  Feedback Report     │
└─────────────────┘     └──────────────────────┘     └─────────────────────┘
```

### Tech Stack (extending Session 1)

| Component | Technology | Notes |
|-----------|-----------|-------|
| Backend | FastAPI + uv | New `/evaluate` endpoints |
| LLM | Anthropic Claude (primary), Azure OpenAI GPT-4o (secondary) – with an abstracted provider layer that can also target a local Ollama model | Via `anthropic` and `openai` SDKs (OpenAI requests are routed through `app/services/llm_provider.py`). |
| Database | Neon PostgreSQL + JSONB | Store rubrics, evaluations, cases |
| Cache | Redis | Cache repeat evaluations on same transcript |
| Frontend | Streamlit | Upload UI, radar charts, evidence drill-down |
| Output Schema | Pydantic models → tool_use / structured_outputs | Guarantees parseable JSON |

---

## Evaluation Rubrics (Detailed)

### Layer 1: Case Fidelity

| Dimension | Weight | 5 (Excellent) | 3 (Adequate) | 1 (Poor) |
|-----------|--------|---------------|---------------|----------|
| **History Accuracy** | 25% | All facts match case; no additions or omissions | Minor inconsistencies; core facts correct | Hallucinated symptoms or contradicts case |
| **Disclosure Pacing** | 20% | Info revealed naturally in response to targeted questions | Occasionally volunteers info unprompted | Dumps entire history at once or withholds key info |
| **Emotional Portrayal** | 20% | Tone matches case description; appropriate affect | Partially aligned; some tonal mismatches | Robotic or wildly incongruent emotional responses |
| **Stays in Character** | 15% | Never breaks character; deflects meta questions | Minor slips (e.g., uses medical jargon inappropriately) | Breaks character; acts as assistant instead of patient |
| **Physical Exam Response** | 20% | Reports findings consistent with case when asked | Reports findings but with minor inconsistencies | Fabricates findings not in case or refuses to engage |

### Layer 2: Student Performance

| Dimension | Weight | 5 (Excellent) | 3 (Adequate) | 1 (Poor) |
|-----------|--------|---------------|---------------|----------|
| **Diagnostic Reasoning** | 25% | Generates broad differential; systematically narrows with targeted questions | Reasonable differential but questioning is unfocused | Anchors on one diagnosis; no systematic approach |
| **History Gathering** | 20% | Covers HPI, PMH, meds, allergies, social, family, ROS systematically | Gets most key elements but misses 1–2 domains | Superficial; misses critical domains |
| **Red Flag Recognition** | 20% | Identifies and follows up on all critical findings promptly | Identifies some red flags but delays follow-up | Misses critical red flags entirely |
| **Empathy & Rapport** | 20% | Active listening, validates emotions, NURSE framework | Some empathic responses but inconsistent | Purely transactional; no emotional acknowledgment |
| **Communication Clarity** | 15% | Avoids jargon; checks understanding; summarizes | Generally clear but occasional jargon without clarification | Overuses jargon; no teach-back or clarification |

---

## Output Schema (Pydantic)

```python
from pydantic import BaseModel, Field
from typing import Literal

class EvidenceCitation(BaseModel):
    turn_number: int = Field(description="Transcript turn number")
    speaker: Literal["Student", "Patient"]
    quote: str = Field(description="Relevant excerpt from that turn")
    relevance: str = Field(description="Why this supports the score")

class DimensionScore(BaseModel):
    dimension: str
    score: int = Field(ge=1, le=5)
    weight: float
    evidence: list[EvidenceCitation]
    rationale: str = Field(description="CoT reasoning for this score")
    strengths: list[str]
    growth_areas: list[str]

class EvaluationResult(BaseModel):
    layer: Literal["case_fidelity", "student_performance"]
    dimensions: list[DimensionScore]
    weighted_total: float
    overall_summary: str
    top_recommendation: str
```

---

## Claude Code Prompts

### Prompt 1: Evaluation Engine Module

```
I'm building an evaluation engine for an LLM-powered simulated patient system 
used in medical education. This extends an existing FastAPI + uv + Neon PostgreSQL 
project (see CLAUDE.md for project conventions).

Create the following in `src/evaluation/`:

1. `schemas.py` — Pydantic models for:
   - `CaseDescription`: demographics, chief_complaint, hpi, pmh, medications, 
     allergies, social_history, family_history, ros, physical_exam_findings, 
     labs, imaging, differential_diagnosis, final_diagnosis, emotional_presentation
   - `TranscriptTurn`: turn_number, speaker (Student|Patient), content
   - `Transcript`: list of TranscriptTurn, metadata (session_id, timestamp)
   - `EvidenceCitation`: turn_number, speaker, quote, relevance
   - `DimensionScore`: dimension, score (1-5), weight, evidence list, rationale, 
     strengths, growth_areas
   - `EvaluationResult`: layer (case_fidelity|student_performance), dimensions list, 
     weighted_total, overall_summary, top_recommendation
   - `EvaluationRequest`: case_description, transcript, layer, rubric_version (optional)
   - `EvaluationResponse`: results for one or both layers, model used, timestamp, 
     token_usage

2. `rubrics.py` — Default rubric definitions as structured dicts:
   - CASE_FIDELITY_RUBRIC with 5 dimensions (history_accuracy, disclosure_pacing, 
     emotional_portrayal, stays_in_character, physical_exam_response)
   - STUDENT_PERFORMANCE_RUBRIC with 5 dimensions (diagnostic_reasoning, 
     history_gathering, red_flag_recognition, empathy_rapport, communication_clarity)
   - Each dimension has: name, weight, anchors for scores 1, 3, 5
   - Function to load custom rubrics from database by version

3. `prompts.py` — Prompt templates:
   - `build_evaluation_prompt(case, transcript, rubric, layer)` that assembles 
     the full LLM-as-judge prompt using XML tags
   - System prompt instructs CoT reasoning before scoring
   - Explicit instructions to cite transcript turn numbers as evidence
   - Debiasing instructions (don't favor verbose responses, evaluate substance)

4. `engine.py` — Core evaluation logic:
   - `evaluate_transcript(request: EvaluationRequest) -> EvaluationResponse`
   - Uses Anthropic Claude via tool_use to enforce structured output
   - Falls back to Azure OpenAI GPT-4o with structured_outputs if Claude fails
   - Redis caching: hash(case_id + transcript_hash + rubric_version + layer) as key
   - Retry logic with exponential backoff
   - Token usage tracking

5. `router.py` — FastAPI endpoints:
   - POST `/api/v1/evaluate` — accepts EvaluationRequest, returns EvaluationResponse
   - POST `/api/v1/evaluate/batch` — evaluate multiple transcripts against same case
   - GET `/api/v1/evaluate/{evaluation_id}` — retrieve stored evaluation
   - GET `/api/v1/rubrics` — list available rubric versions
   - POST `/api/v1/rubrics` — create custom rubric

Requirements:
- Use `anthropic` SDK with tool_use for structured output from Claude
- Use `openai` SDK with response_format for GPT-4o fallback
- All secrets from environment variables (ANTHROPIC_API_KEY, AZURE_OPENAI_*, REDIS_URL, DATABASE_URL)
- Comprehensive logging with structlog
- Type hints everywhere; all models validated with Pydantic v2
- Write tests in `tests/test_evaluation.py` with mocked LLM responses
```

### Prompt 2: Rubric Management & Database Layer

```
Extend the evaluation system with database-backed rubric management. 
The project uses Neon PostgreSQL with JSONB columns (see CLAUDE.md).

Create/modify:

1. `src/database/models.py` — Add SQLAlchemy models:
   - `Rubric`: id, name, layer (case_fidelity|student_performance), version, 
     dimensions (JSONB), created_by, created_at, is_default
   - `Evaluation`: id, session_id, case_id, transcript_hash, layer, rubric_id, 
     result (JSONB storing full EvaluationResult), model_used, token_usage, 
     created_at, duration_ms
   - `Case`: id, title, specialty, difficulty, case_data (JSONB storing CaseDescription), 
     created_by, created_at

2. `src/database/migrations/` — Alembic migration for new tables

3. `src/evaluation/rubric_service.py`:
   - CRUD operations for rubrics
   - `get_default_rubric(layer)` — returns latest default
   - `get_rubric_by_version(layer, version)` — specific version
   - `create_rubric(rubric_data)` — validates dimensions have correct structure
   - `export_rubric_yaml(rubric_id)` / `import_rubric_yaml(yaml_str)` — 
     for sharing rubrics between institutions
   - Seed function that loads the default rubrics from rubrics.py on first run

4. `src/evaluation/evaluation_service.py`:
   - `store_evaluation(evaluation_result, metadata)` — persist to Neon
   - `get_evaluations_for_case(case_id)` — all evaluations for a case
   - `get_evaluations_for_student(student_id)` — longitudinal tracking
   - `compute_aggregate_stats(evaluations)` — mean, std, trend per dimension
   - `compare_evaluations(eval_ids)` — side-by-side comparison

Requirements:
- Use async SQLAlchemy with asyncpg
- JSONB columns for flexible schema evolution
- Indexes on (case_id, layer), (session_id), (created_at)
- Connection pooling via SQLAlchemy async engine
- All operations wrapped in proper transaction management
```

### Prompt 3: Streamlit Evaluation Dashboard

```
Build a Streamlit dashboard for the evaluation system. This extends the 
existing Streamlit app from Session 1 (see CLAUDE.md for conventions).

Create `src/frontend/pages/3_Evaluation_Dashboard.py`:

## Page Layout

### Sidebar
- Model selector (Claude Sonnet 4, GPT-4o)
- Rubric version selector (dropdown populated from API)
- Evaluation layer checkboxes (Case Fidelity, Student Performance, or Both)

### Main Area — Tab Layout

**Tab 1: "Run Evaluation"**
- Two-column upload area:
  - Left: Case description upload (JSON) or select from saved cases dropdown
  - Right: Transcript upload (JSON or plain text with "Student:" / "Patient:" prefixes)
- "Preview" expander showing parsed case summary and transcript preview
- Big "Run Evaluation" button
- Results display after evaluation:
  - Radar/spider chart (plotly) showing dimension scores for each layer
  - Expandable cards per dimension: score badge, rationale text, evidence citations 
    with transcript turn references highlighted
  - Overall weighted score displayed prominently
  - "Strengths" and "Growth Areas" summary sections
  - Download evaluation as PDF button

**Tab 2: "Batch Evaluation"**
- Upload multiple transcripts (ZIP or multi-file)
- Select case to evaluate against
- Progress bar during batch processing
- Results table: session_id, weighted_case_fidelity, weighted_student_performance
- Box plot visualization across batch

**Tab 3: "Analytics"**
- Date range selector
- Line charts: dimension scores over time (longitudinal student tracking)
- Heatmap: dimension × session matrix
- Distribution histograms per dimension
- Export to CSV

## Technical Requirements
- Use `httpx` async client to call FastAPI evaluation endpoints
- Plotly for all charts (radar, line, box, heatmap)
- st.cache_data for API responses with 5-minute TTL
- Error handling with user-friendly messages
- Loading spinners during LLM evaluation (can take 10-30s)
- Session state management for multi-step workflows
- Responsive layout using st.columns

## Sample Data
- Include a `sample_data/` directory with:
  - `sample_case_chest_pain.json` — 55yo M with atypical chest pain
  - `sample_transcript_good.json` — example of strong student performance
  - `sample_transcript_poor.json` — example of weak student performance
- These load as defaults when the page first opens for demo purposes
```


---

## Implementation Sequence

1. **Run Prompt 1** → Get evaluation engine with schemas, prompts, and API endpoints
2. **Test with sample data** → Manually verify one case + transcript evaluation
3. **Run Prompt 2** → Add database persistence and rubric management
4. **Run Prompt 3** → Build Streamlit dashboard
5. **Integration test** → End-to-end: upload case → upload transcript → see evaluation
6. **Calibration exercise** → Have faculty score 5 transcripts, compare to LLM scores, iterate rubrics

---

## Key References

Zheng, L., Chiang, W.-L., Sheng, Y., Zhuang, S., Wu, Z., Zhuang, Y., ... & Stoica, I. (2023). "Judging LLM-as-a-judge with MT-Bench and Chatbot Arena." Advances in Neural Information Processing Systems (NeurIPS), 36.

Taubenfeld, A., Dover, Y., Reichart, R., & Goldstein, A. (2024). "Systematic Biases in LLM Simulations of Debates." Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP).

Kim, S., Suk, J., Longpre, S., Lin, B. Y., Shin, J., Welleck, S., ... & Seo, M. (2024). "Prometheus 2: An Open Source Language Model Specialized in Evaluating Other Language Models." Proceedings of the 2024 Conference on Empirical Methods in Natural Language Processing (EMNLP).

Shankar, S., Zamfirescu-Pereira, J. D., Hartmann, B., Parameswaran, A. G., & Arawjo, I. (2024). "Who Validates the Validators? Aligning LLM-Assisted Evaluation of LLM Outputs with Human Preferences." Proceedings of the 37th Annual ACM Symposium on User Interface Software and Technology (UIST '24).
