# AI-Assisted Medical Case Generator

A full-stack application that generates realistic medical cases using LLMs, persists them to a Neon (Postgres) database, and brings them to life with voice synthesis. Built as a learning resource for CS students exploring healthcare applications.

## Architecture Overview

```
┌──────────────┐       ┌──────────────────┐       ┌────────────┐
│  Streamlit   │──────▶│  FastAPI Backend  │──────▶│  Neon DB   │
│  Frontend    │◀──────│  + Redis Cache    │◀──────│ (Postgres) │
└──────────────┘       └──────────────────┘       └────────────┘
                              │
                    ┌─────────┴─────────┐
                    │                   │
              ┌─────▼─────┐     ┌──────▼──────┐
              │  LLM      │     │    Voice     │
              │Provider   │     │  Generation  │
              │(OpenAI / Ollama)│
              └───────────┘     └─────────────┘
```

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Frontend | Streamlit (Python) | Rapid UI prototyping; replaceable with TS/Tailwind/Vite later |
| Backend | FastAPI | Async API with automatic OpenAPI docs |
| Caching | Redis | Low-latency caching for repeated queries |
| Database | Neon (Postgres) | Serverless Postgres for case persistence |
| LLM | OpenAI or a local Ollama model (configurable via `LLM_PROVIDER`) | Medical case generation with validated schemas. The code includes a provider layer (`app/services/llm_provider.py`) that abstracts away the backend and retries/validates JSON from less strict models. |
| Voice | TBD | Text-to-speech for saved cases |

---

## Prerequisites

| Tool | Install |
|------|---------|
| **Python 3.11+** | [python.org](https://www.python.org/downloads/) |
| **uv** | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| **Redis** | `brew install redis` (macOS) or [redis.io/docs](https://redis.io/docs/getting-started/) |
| **Ollama (optional)** | Install via `brew install ollama` or follow [https://ollama.ai/docs](https://ollama.ai/docs). Required only if you set `LLM_PROVIDER=ollama`. |

> **What is uv?** — [uv](https://docs.astral.sh/uv/) is a fast Python package manager written in Rust. It replaces `pip`, `pip-tools`, `venv`, and more in a single binary. We use it for speed and reproducibility.

---

## Getting Started

### 1. Clone the repo

```bash
git clone https://github.com/<your-username>/AI-assisted-LLM-apps.git
cd AI-assisted-LLM-apps
```

### 2. Create a virtual environment with uv

```bash
uv venv                  # creates .venv/ in the project root
source .venv/bin/activate # activate it (macOS/Linux)
# On Windows: .venv\Scripts\activate
```

### 3. Initialize the project (first time only)

> 💡 **Tip:** you can run the app against either OpenAI's hosted API or a local
> Ollama model.  Set `LLM_PROVIDER=openai` (default) or `LLM_PROVIDER=ollama` and
> configure `OLLAMA_MODEL`/`OLLAMA_BASE_URL`.  See `.env.example` and
> `app/services/llm_provider.py` for details.


```bash
uv init                  # creates pyproject.toml if it doesn't exist
```

### 4. Add dependencies

```bash
# Core dependencies
uv add fastapi "uvicorn[standard]" streamlit openai pydantic redis asyncpg

# Dev dependencies
uv add --dev pytest ruff pip-audit piper-tts
```

`uv add` installs the package **and** records it in `pyproject.toml` automatically.

### 5. Lock dependencies

```bash
uv lock                  # generates uv.lock from pyproject.toml
```

> **Why lock?** — `uv.lock` pins every transitive dependency to an exact version. Anyone who runs `uv sync` gets a byte-for-byte identical environment. **Commit `uv.lock` to version control.**

### 6. Sync an existing environment (for collaborators)

```bash
uv sync                  # installs exactly what uv.lock specifies
```

### Quick reference

| Task | Command |
|------|---------|
| Create venv | `uv venv` |
| Add a package | `uv add <pkg>` |
| Add a dev package | `uv add --dev <pkg>` |
| Remove a package | `uv remove <pkg>` |
| Re-lock after edits | `uv lock` |
| Install from lockfile | `uv sync` |
| Run a script | `uv run python script.py` |

---

## Running the Application

You need **three terminals** (plus Redis) to run the full stack. Start them in order:

### 1. Start Redis

```bash
redis-server
```

Redis must be running before the backend starts.

### 2. Start the FastAPI backend (Terminal 1)

```bash
uv run uvicorn app.main:app --reload
```

Runs on **http://localhost:8000** by default. API docs are at `/docs`.

### 3. Start the Case Generator frontend (Terminal 2)

> **If you're using Ollama**: make sure the Ollama server is running (`ollama serve`) and
> that the model specified by `OLLAMA_MODEL` has been pulled (`ollama pull <model>`).


```bash
uv run streamlit run frontend/streamlit_app.py
```

Runs on **http://localhost:8501**. This is the main UI for generating, browsing, and editing medical cases.

### 4. Start the Patient Interview frontend (Terminal 3)

```bash
uv run streamlit run frontend/interview_app.py --server.port 8502
```

Runs on **http://localhost:8502**. Voice-based patient interview practice using audio models.

### 5. Start the Evaluation Dashboard (Terminal 4)

```bash
uv run streamlit run frontend/evaluation_dashboard.py --server.port 8503
```

Runs on **http://localhost:8503**. Upload transcripts for multidimensional evaluation with radar-chart results.

### Quick start summary

| Service | Command | URL |
|---------|---------|-----|
| Redis | `redis-server` | `localhost:6379` |
| FastAPI backend | `uv run uvicorn app.main:app --reload` | `localhost:8000` |
| Case Generator UI | `uv run streamlit run frontend/streamlit_app.py` | `localhost:8501` |
| Patient Interview | `uv run streamlit run frontend/interview_app.py --server.port 8502` | `localhost:8502` |
| Evaluation Dashboard | `uv run streamlit run frontend/evaluation_dashboard.py --server.port 8503` | `localhost:8503` |

---

## .gitignore — Set This Up First

**Before your very first commit**, make sure `.gitignore` is in place. This is not optional — it is the single most important step for protecting API keys and credentials.

### Why order matters

Git tracks files permanently. If you accidentally commit `.env` containing your `OPENAI_API_KEY` and then add `.env` to `.gitignore` later, **the key is still in your git history**. Anyone who clones the repo can find it. Rotating a leaked key costs time; a leaked key on a public repo can cost real money within minutes (bots actively scan GitHub for exposed secrets).

> **Rule: `.gitignore` goes in your very first commit — before any application code.**

### What we ignore and why

| Entry | Why |
|-------|-----|
| `.env` / `.env.*` | Contains API keys, database credentials, and other secrets. This is the most critical entry in the file. |
| `__pycache__/` / `*.py[cod]` | Python bytecode files. Generated on every run, differ per machine, and add noise to diffs. |
| `.venv/` | The virtual environment. Hundreds of MBs of installed packages — reproducible via `uv sync`, never committed. |
| `.vscode/` / `.idea/` | IDE settings are personal to each developer. Committing them causes merge conflicts and overrides teammates' preferences. |
| `.DS_Store` | macOS Finder metadata. Invisible junk files that have no place in a repo. |
| `dump.rdb` | Redis persistence file created when Redis saves to disk locally. Machine-specific, not project state. |
| `*.sql.bak` | Database backup dumps that may contain real patient-like data or credentials in connection strings. |

### What if you already committed a secret?

If a `.env` or any secret file was committed by mistake:

```bash
# 1. Remove it from tracking (keeps the local file)
git rm --cached .env

# 2. Commit the removal
git commit -m "Remove .env from tracking"

# 3. IMMEDIATELY rotate the exposed key
#    - Go to your OpenAI dashboard and regenerate the API key
#    - Update your local .env with the new key
#    - Any key that touched a public repo should be considered compromised
```

For a deeper scrub of git history, look into [`git-filter-repo`](https://github.com/newren/git-filter-repo) or [BFG Repo-Cleaner](https://rtyley.github.io/bfg-repo-cleaner/). But prevention (`.gitignore` first) is always better than cleanup.

---

## Supply-Chain Security

Open-source dependencies are an attack surface. We use two complementary tools:

### Socket.dev

This repo is connected to [Socket.dev](https://socket.dev/) on GitHub. Socket automatically scans every PR for:

- **Typosquatting** — packages with names similar to popular ones
- **Install scripts** — packages that execute code on `pip install`
- **Obfuscated code** — minified or encoded payloads
- **Known malware** — flagged packages in the ecosystem

No setup required on your end — Socket runs as a GitHub App on the public repo. Review its PR comments before merging.

### pip-audit

`pip-audit` checks installed packages against the [OSV](https://osv.dev/) vulnerability database.

```bash
# Run manually
uv run pip-audit

# Example output:
# Name        Version  ID                  Fix Versions
# ----------  -------  ------------------  ------------
# requests    2.25.1   PYSEC-2023-74       2.31.0
```

Run `pip-audit` before every release and in CI. Fix findings by upgrading the flagged package:

```bash
uv add <package>@latest
uv lock
```

---

## Structured LLM Outputs

Every LLM call in this project uses **structured outputs** — we define a Pydantic schema for the expected response and pass it as `response_format`. The model is constrained to return valid JSON matching that schema. No hand-parsing, no regex, no "please respond in JSON" prompts.

### Why this matters

- **Type safety** — responses are parsed into Python objects automatically
- **No malformed JSON** — the API guarantees schema compliance
- **Explicit refusals** — if the model refuses (e.g., safety filters), `.parsed` is `None` and `.refusal` contains the reason

### Pattern

```python
from pydantic import BaseModel
from openai import OpenAI

# 1. Define your schema
class MedicalCase(BaseModel):
    case_title: str
    patient_age: int
    patient_sex: str
    chief_complaint: str
    history_of_present_illness: str
    past_medical_history: list[str]
    medications: list[str]
    physical_exam_findings: str
    differential_diagnosis: list[str]
    final_diagnosis: str
    management_plan: str

# 2. Call the API with response_format
client = OpenAI()

completion = client.chat.completions.parse(
    model="gpt-4o",
    messages=[
        {
            "role": "system",
            "content": "You are a medical education assistant. Generate a realistic clinical case."
        },
        {
            "role": "user",
            "content": "Generate an emergency medicine case involving chest pain."
        },
    ],
    response_format=MedicalCase,
)

# 3. Use the parsed object directly
case = completion.choices[0].message.parsed

if case is None:
    # Model refused — check completion.choices[0].message.refusal
    print("Refused:", completion.choices[0].message.refusal)
else:
    print(case.case_title)
    print(case.differential_diagnosis)
```

### Rules we follow

1. **Every LLM call gets a Pydantic model** — no unstructured completions.
2. **Schemas live in a dedicated module** — `app/schemas/` — so they're reusable and testable.
3. **Always handle refusals** — check `.parsed` before using the result.

---

## Project Structure (planned)

```
AI-assisted-LLM-apps/
├── app/
│   ├── api/              # FastAPI route handlers (cases, transcripts)
│   ├── evaluation/       # Evaluation engine, rubrics, and API router
│   ├── schemas/          # Pydantic models (LLM + DB)
│   ├── services/         # Business logic (LLM calls, caching)
│   ├── db/               # Neon/Postgres connection + queries
│   ├── config.py         # Settings loaded from .env
│   └── main.py           # FastAPI app entrypoint
├── frontend/
│   ├── api_client.py             # Shared HTTP client for the backend API
│   ├── streamlit_app.py          # Case Generator UI
│   ├── interview_app.py          # Patient Interview UI (voice)
│   └── evaluation_dashboard.py   # Evaluation Dashboard UI
├── sample_data/           # Example transcripts for evaluation testing
├── tests/
├── .env.example           # Template for required env vars (safe to commit)
├── .gitignore             # Keeps secrets and generated files out of git
├── pyproject.toml         # Project metadata + dependencies
├── uv.lock                # Pinned dependency lockfile
├── LICENSE                # MIT License
└── README.md
```

---

## Environment Variables

Copy the template and fill in your values:

```bash
cp .env.example .env
```

Then edit `.env` with your actual keys (**never commit this file** — it is in `.gitignore`):

```env
OPENAI_API_KEY=sk-...
DATABASE_URL=postgresql+asyncpg://<user>:<pass>@<host>/<db>?sslmode=require
REDIS_URL=redis://localhost:6379
```

> **Why `.env.example`?** — It is safe to commit because it contains only placeholder values. It tells collaborators which variables are required without exposing real secrets.

---

## Code Quality with Ruff

[Ruff](https://docs.astral.sh/ruff/) is a Python linter and formatter written in Rust. It replaces tools like `flake8`, `isort`, `pycodestyle`, and `black` in a single, fast binary — which is why we include it as our only code-quality dev dependency.

### What `ruff check` does

`ruff check .` scans every Python file in the project and flags issues such as:

- **Unused imports and variables** — dead code that clutters files
- **Style violations** — inconsistent spacing, line length, naming conventions
- **Common bugs** — mutable default arguments, bare `except:` clauses, f-strings missing placeholders
- **Import ordering** — ensures imports are grouped and sorted consistently

```bash
# Lint the entire project
uv run ruff check .

# Auto-fix anything Ruff can safely correct (unused imports, sort order, etc.)
uv run ruff check . --fix

# Format code (consistent style like black)
uv run ruff format .
```

Example output:

```
app/services/llm.py:12:1: F401 [*] `os` imported but unused
app/api/cases.py:45:5: B006 Do not use mutable data structures for argument defaults
Found 2 errors.
[*] 1 fixable with the `--fix` option.
```

Each rule has a code (e.g., `F401`, `B006`) — you can look these up in the [Ruff rule reference](https://docs.astral.sh/ruff/rules/) for a full explanation.

> **Tip:** Run `ruff check .` before every commit. If you want to enforce this automatically, consider adding a [pre-commit hook](https://docs.astral.sh/ruff/integrations/#pre-commit).

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) when available. In short:

- Keep PRs small and focused
- Run `uv run ruff check .` before pushing
- Run `uv run pip-audit` to check for vulnerabilities
- All LLM calls must use structured outputs with a defined schema

---

## License

This project is licensed under the [MIT License](LICENSE).

MIT was chosen because it is the most permissive common open-source license — anyone can use, modify, and distribute this code (including in commercial projects) with no restrictions beyond preserving the copyright notice. This makes it ideal for an educational showcase where the goal is maximum reuse.
