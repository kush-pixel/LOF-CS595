"""LLM provider abstraction, allowing easy switching between OpenAI and Ollama.

The rest of the application should import ``provider`` and ``parse_with_schema``
rather than instantiating ``openai.AsyncOpenAI`` directly.  Configuration is driven
by ``app.config.settings``:

* ``LLM_PROVIDER``: either "openai" (default) or "ollama".
* ``OLLAMA_MODEL``: which model to use when ``LLM_PROVIDER=ollama`` (defaults
  to "llama3.2" in this repo).
* ``OLLAMA_API_BASE_URL``: base URL for the Ollama OpenAI-compatible API
  (defaults to ``http://localhost:11434/v1``).

The module also contains a small helper that attempts to validate the response
against a Pydantic schema and retries once for Ollama if the first parse fails.
"""

from __future__ import annotations

from typing import Any, Type

import openai
from pydantic import BaseModel, ValidationError

from app.config import settings


class LLMProvider:
    def __init__(self) -> None:
        self.name = settings.LLM_PROVIDER.lower()
        if self.name == "ollama":
            base = settings.OLLAMA_API_BASE_URL or "http://localhost:11434/v1"
            self.client = openai.AsyncOpenAI(
                api_key="ollama",
                base_url=base,
            )
        else:
            self.client = openai.AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

        # create a synchronous client for cases where async is inconvenient
        if self.name == "ollama":
            self.sync_client = openai.OpenAI(api_key="ollama", base_url=base)
        else:
            self.sync_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

    @property
    def is_ollama(self) -> bool:
        return self.name == "ollama"


def provider() -> LLMProvider:
    """Return a fresh provider instance.  We avoid a module-level singleton so
    tests and different parts of the app can reconfigure the environment if
    needed without having stale state.
    """

    return LLMProvider()


async def parse_with_schema(
    client: Any,
    model: str,
    messages: list[dict[str, Any]],
    schema: Type[BaseModel],
    **kwargs: Any,
) -> BaseModel:
    """Ask the model to return structured JSON and validate it.

    The OpenAI ``responses.parse`` helper can take a Pydantic model directly.  In
    practice Ollama sometimes produces slightly malformed JSON; we therefore
    fall back to manual validation and, when the configured provider is Ollama,
    retry a couple of times before giving up.
    """

    # attempt using the built-in parse functionality first
    try:
        print(f"Attempting to parse with built-in response parsing for model {client, model}...")

        resp = await client.responses.parse(
            model=model,
            input=messages,
            text_format=schema,
            **kwargs,
        )
        parsed = resp.output_parsed
        if parsed is not None:
            return parsed
        # ``output_parsed`` may be None if the provider didn't strictly
        # implement parsing; we'll fall through to the manual code below.
    except Exception:
        # we intentionally swallow the exception here because manual parsing
        # below may still succeed and we want to retry when using Ollama.
        parsed = None

    # manual path: grab whatever text the model returned and validate
    # using Pydantic directly.
    attempts = 1
    if settings.LLM_PROVIDER.lower() == "ollama":
        attempts = 3

    last_exc: Exception | None = None
    for attempt in range(attempts):
        try:
            # call the more generic chat/completions endpoint so we can capture
            # the ``output_text``; this works whether we're talking to real
            # OpenAI or to Ollama's compatibility layer.
            resp = await client.chat.completions.create(
                model=model,
                messages=messages,
                **kwargs,
            )
            text = resp.choices[0].message.get("content", "")
            return schema.model_validate_json(text)
        except (ValidationError, Exception) as exc:
            last_exc = exc
            if attempt < attempts - 1:
                # simple backoff
                import asyncio

                await asyncio.sleep(1 + attempt)
                continue
            # re-raise the most recent error
            raise ValueError(
                f"failed to parse LLM output after {attempt+1} attempts: {exc}"
            )

    # unreachable; return type satisfied for mypy
    raise RuntimeError("unhandled parsing branch")
