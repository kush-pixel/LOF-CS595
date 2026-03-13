"""Application configuration loaded from environment variables."""

from __future__ import annotations

import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
    OPENAI_AUDIO_MODEL: str = os.getenv("OPENAI_AUDIO_MODEL", "gpt-4o-audio-preview")
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://localhost:5432/medcases")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # LLM provider configuration – choose between "openai" or "ollama".
    # When using Ollama the local server should be running (`ollama serve`).
    # The default is still OpenAI for backwards compatibility.
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "openai")
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.2")
    OLLAMA_API_BASE_URL: str = os.getenv("OLLAMA_API_BASE_URL", "http://localhost:11434/v1")


settings = Settings()
