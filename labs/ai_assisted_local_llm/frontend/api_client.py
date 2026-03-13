"""Thin requests wrapper for the Medical Case Generator API."""

from __future__ import annotations

import os

import requests

BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


def _url(path: str) -> str:
    return f"{BASE_URL}{path}"


# def generate_case(specialty: str | None = None, prompt: str | None = None, difficulty: str | None = None) -> dict:
#     body = {}
#     if specialty:
#         body["specialty"] = specialty
#     if prompt:
#         body["prompt"] = prompt
#     if difficulty:
#         body["difficulty"] = difficulty
#     resp = requests.post(_url("/api/v1/cases/generate"), json=body, timeout=120)
#     resp.raise_for_status()
#     return resp.json()

def generate_case(
    specialty: str | None = None,
    prompt: str | None = None,
    difficulty: str | None = None,
    llm_provider: str | None = None,   # "openai" or "ollama"
    llm_model: str | None = None,      # e.g., "llama3.2", "gemma3", or OpenAI model
) ->dict:
    body: dict = {}
    if specialty:
        body["specialty"] = specialty
    if prompt:
        body["prompt"] = prompt
    if difficulty:
        body["difficulty"] = difficulty

    if llm_provider:
        body["llm_provider"] = llm_provider
    if llm_model:
        body["llm_model"] = llm_model

    print(f"Requesting case generation with body: {body}")

    resp = requests.post(_url("/api/v1/cases/generate"), json=body, timeout=600)
    resp.raise_for_status()
    return resp.json()

def create_case(payload: dict) -> dict:
    resp = requests.post(_url("/api/v1/cases/"), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def list_cases(
    page: int = 1,
    page_size: int = 20,
    specialty: str | None = None,
    search: str | None = None,
) -> dict:
    params: dict = {"page": page, "page_size": page_size}
    if specialty:
        params["specialty"] = specialty
    if search:
        params["search"] = search
    resp = requests.get(_url("/api/v1/cases/"), params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_case(case_id: str) -> dict:
    resp = requests.get(_url(f"/api/v1/cases/{case_id}"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_case_by_number(case_number: int) -> dict:
    resp = requests.get(_url(f"/api/v1/cases/by-number/{case_number}"), timeout=30)
    resp.raise_for_status()
    return resp.json()


def update_case(case_id: str, payload: dict) -> dict:
    resp = requests.put(_url(f"/api/v1/cases/{case_id}"), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def patch_case(case_id: str, payload: dict) -> dict:
    resp = requests.patch(_url(f"/api/v1/cases/{case_id}"), json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()


def delete_case(case_id: str) -> None:
    resp = requests.delete(_url(f"/api/v1/cases/{case_id}"), timeout=30)
    resp.raise_for_status()


def save_transcript(conversation_id: str, case_number: int, transcript: list[dict]) -> dict:
    resp = requests.post(
        _url("/api/v1/transcripts/"),
        json={
            "conversation_id": conversation_id,
            "case_number": case_number,
            "transcript": transcript,
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()
