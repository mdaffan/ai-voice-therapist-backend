"""Service – Text-to-speech helpers using OpenAI TTS models."""

from __future__ import annotations

import tempfile
from pathlib import Path

from openai import AsyncOpenAI

from app.infra.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def synthesize(
    text: str,
    *,
    model: str = "tts-1",
    voice: str = "alloy",
    response_format: str = "pcm",
    **extra,
) -> bytes:
    """Return full audio as bytes (blocking)."""

    response = await client.audio.speech.create(
        model=model,
        voice=voice,
        input=text,
        response_format=response_format,
        **extra,
    )

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


async def synthesize_stream(
    text: str,
    *,
    model: str = "tts-1",
    voice: str = "alloy",
    chunk_size: int | None = None,
    **optional_params,
):
    """Yield audio bytes incrementally."""

    try:
        async with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            response_format="mp3",
            **optional_params,
        ) as resp:
            async for chunk in resp.iter_bytes(chunk_size=chunk_size or 4096):
                yield chunk
            return
    except Exception as exc:  # pragma: no cover – network issues
        import logging

        logging.warning("TTS streaming failed, fallback: %s", exc)

    # fallback to full synth
    yield await synthesize(text, model=model, voice=voice, **optional_params) 