CREATE TABLE IF NOT EXISTS cases (
    case_id     UUID PRIMARY KEY,
    case_title  TEXT NOT NULL DEFAULT '',
    specialty   TEXT NOT NULL DEFAULT 'general',
    difficulty  TEXT NOT NULL DEFAULT 'medium',
    case_data   JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Auto-incrementing case number for human-friendly lookup
DO $$ BEGIN
    ALTER TABLE cases ADD COLUMN case_number SERIAL;
EXCEPTION
    WHEN duplicate_column THEN NULL;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS idx_cases_case_number ON cases (case_number);

CREATE INDEX IF NOT EXISTS idx_cases_specialty ON cases (specialty);
CREATE INDEX IF NOT EXISTS idx_cases_difficulty ON cases (difficulty);
CREATE INDEX IF NOT EXISTS idx_cases_data_gin ON cases USING GIN (case_data);

-- Trigram index for fast ILIKE title search
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE INDEX IF NOT EXISTS idx_cases_title_trgm ON cases USING GIN (case_title gin_trgm_ops);

-- Interview transcripts
CREATE TABLE IF NOT EXISTS interview_transcripts (
    conversation_id  UUID PRIMARY KEY,
    case_number      INT NOT NULL,
    transcript       JSONB NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_transcripts_case_number ON interview_transcripts (case_number);

-- Evaluations
CREATE TABLE IF NOT EXISTS evaluations (
    evaluation_id  UUID PRIMARY KEY,
    session_id     TEXT NOT NULL DEFAULT 'anonymous',
    layer          TEXT NOT NULL,
    result         JSONB NOT NULL,
    model_used     TEXT NOT NULL,
    token_usage    JSONB NOT NULL DEFAULT '{}',
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_evaluations_session ON evaluations (session_id);
CREATE INDEX IF NOT EXISTS idx_evaluations_layer ON evaluations (layer);
CREATE INDEX IF NOT EXISTS idx_evaluations_created ON evaluations (created_at);
