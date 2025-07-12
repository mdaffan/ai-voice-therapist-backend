"""Text-to-speech utilities wrapped for FastAPI endpoint usage.

This module exposes a single coroutine – ``synthesize`` – which generates a
spoken MP3 for the supplied text *without* writing anything to disk. The raw
bytes are returned so the API layer can decide how to stream or cache them.

It intentionally contains **no** top-level ``asyncio.run`` calls because the
module is imported by ``app.main`` inside a running FastAPI application where a
loop is already active. Running a second loop would blow up with the
``RuntimeError: asyncio.run() cannot be called from a running event loop`` that
you just encountered.
"""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
from openai import AsyncOpenAI

# Initialised once for module reuse; reads OPENAI_API_KEY from env
client = AsyncOpenAI()


# Default model/voice can be overridden via environment variables supported by
# LiteLLM (e.g. ``LITELLM_TTS_MODEL``) or by passing explicit kwargs into
# ``synthesize``.


async def synthesize(
    text: str,
    *,
    model: str = "tts-1",  # OpenAI model name
    voice: str = "alloy",
    response_format: str = "pcm",
    **extra,
) -> bytes:
    """Blocking TTS convenience – returns the full MP3 as bytes."""

    response = await client.audio.speech.create(
        model="tts-1",
        voice=voice,
        input=text,
        response_format="pcm",
        **extra,
    )

    # The SDK returns an object that can .audio or stream_to_file; easiest is to
    # stream to tempfile to capture bytes.
    with tempfile.NamedTemporaryFile(suffix=f".{response_format}", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        response.stream_to_file(tmp_path)
        tmp.seek(0)
        data = tmp.read()

    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass

    return data


# ---------- Streaming variant ----------

async def synthesize_stream(
    text: str,
    *,
    model: str = "tts-1",
    voice: str = "alloy",
    chunk_size: int | None = None,
    **optional_params,
):
    """Yield audio bytes incrementally as they are produced by the provider.

    Falls back to yielding the full MP3 at once if streaming isn't supported.
    """

    try:
        async with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
            **optional_params,
        ) as resp:
            # New SDK: resp.iter_bytes()
            async for chunk in resp.iter_bytes(chunk_size=chunk_size or 4096):
                yield chunk
            return
    except Exception as e:
        import logging

        logging.warning("TTS streaming failed – fallback to full synth: %s", e)

    # Fallback – no streaming; emit full file
    yield await synthesize(text, model=model, voice=voice, **optional_params)