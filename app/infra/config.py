# infra/config.py
"""Centralised configuration using python-dotenv (simple).

Loads variables from a local `.env` if present and exposes a `settings` object
with attribute access. This keeps things readable without the overhead of
Pydantic while still allowing type-like access semantics.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

from dotenv import load_dotenv


# Read .env into os.environ (no-op if file is missing)
load_dotenv()


def _env(key: str, default: str | None = None) -> str:
    """Tiny helper for getenv with default."""

    return os.getenv(key, default or "")


# Single namespace exported for easy imports
settings = SimpleNamespace(
    # Core
    api_port=int(_env("PORT", "9000")),

    # Vendor keys
    openai_api_key=_env("OPENAI_API_KEY"),
    anthropic_api_key=_env("ANTHROPIC_API_KEY"),

    # Model names
    gpt_model=_env("GPT_MODEL", "gpt-4o"),
    claude_model=_env("CLAUDE_MODEL", "anthropic/claude-3-7-sonnet-latest"),
    stt_model=_env("STT_MODEL", "whisper-1"),
    tts_model=_env("TTS_MODEL", "tts-1"),
)


# Ensure essential keys are present for SDKs
if settings.openai_api_key:
    os.environ.setdefault("OPENAI_API_KEY", settings.openai_api_key)

if settings.anthropic_api_key:
    os.environ.setdefault("ANTHROPIC_API_KEY", settings.anthropic_api_key) 