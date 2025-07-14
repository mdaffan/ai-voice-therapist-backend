"""Service – Text-to-speech helpers using OpenAI TTS models."""

from __future__ import annotations

import tempfile
from pathlib import Path

from openai import AsyncOpenAI
import requests

from app.infra.config import settings

client = AsyncOpenAI(api_key=settings.openai_api_key)



async def synthesize_stream(
    text: str,
    *,
    model: str = "gpt-4o-mini-tts",
    voice: str = "nova",
    chunk_size: int | None = None,
    **optional_params,
):
    """Yield audio bytes incrementally."""
    # If Deepgram usage is enabled, delegate to the Deepgram helper.
    if settings.use_deepgram and settings.deepgram_api_key:
        async for chunk in synthesize_stream_deepgram(
            text,
            chunk_size=chunk_size,
            **optional_params,
        ):
            yield chunk
        return
    instructions = """Voice: Soft, calm, and empathetic, with a gentle, steady cadence that fosters safety and trust.\n\nTone: Compassionate, non-judgmental, and reflective, encouraging self-exploration and validating the speaker’s feelings.\n\nDialect: Neutral and professional, free of jargon while remaining warm and approachable.\n\nPronunciation: Gentle and clear, allowing comfortable pauses for reflection and using soothing intonation.\n\nFeatures: Employs reflective listening, affirmations, open-ended questions, and gentle prompts that support emotional expression and insight."""
    try:
        async with client.audio.speech.with_streaming_response.create(
            model=model,
            voice=voice,
            input=text,
            instructions=instructions,
            response_format="mp3",
            **optional_params,
        ) as resp:
            async for chunk in resp.iter_bytes(chunk_size=chunk_size or 4096):
                yield chunk
            return
    except Exception as exc:  # pragma: no cover – network issues
        import logging

        logging.warning("TTS streaming failed, fallback: %s", exc)

# --------------------------------------------------------------------------- #
# Deepgram TTS – stream bytes directly from the Deepgram “/v1/speak” endpoint #
# --------------------------------------------------------------------------- #

async def synthesize_stream_deepgram(
    text: str,
    *,
    model: str = "aura-asteria-en",   # Deepgram Aura voice model
    encoding: str = "mp3",            # mp3, wav, flac, etc.
    sample_rate: int | None = 24000,   # 24 kHz recommended for Aura voices
    chunk_size: int | None = None,
    **optional_params,
):
    """Stream TTS audio from Deepgram.

    This opens an HTTP chunked stream to Deepgram’s `/v1/speak` endpoint and
    yields raw audio bytes so callers can forward them to the client
    """

    url = "https://api.deepgram.com/v1/speak"

    params: dict[str, str | int] = {
        "model": model,
        "encoding": encoding,
    }
    if sample_rate is not None:
        params["sample_rate"] = sample_rate

    # Allow arbitrary query params (e.g., stability, style) via `query_params`.
    params.update(optional_params.pop("query_params", {}))

    headers = {
        "Authorization": f"Token {settings.deepgram_api_key}",
        "Content-Type": "application/json",
    }
    payload = {
    "text": text
}
    response = requests.post(url, headers=headers, json=payload, stream=True)
    for chunk in response.iter_content(chunk_size=1024):
        yield chunk
   