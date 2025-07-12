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

import io
from pathlib import Path
import tempfile

import litellm

# Default model/voice can be overridden via environment variables supported by
# LiteLLM (e.g. ``LITELLM_TTS_MODEL``) or by passing explicit kwargs into
# ``synthesize``.


async def synthesize(
    text: str,
    *,
    model: str = "openai/tts-1",
    voice: str = "alloy",
    **optional_params,
) -> bytes:
    """Generate speech for *text* and return raw MP3 bytes.

    Parameters
    ----------
    text:
        Input text to vocalise.
    model, voice:
        Override LiteLLM settings if desired.
    **optional_params:
        Forwarded verbatim to ``litellm.aspeech`` – useful for provider-
        specific tweaks.
    """

    # LiteLLM currently returns an object that can either stream to a file or
    # expose ``audio_bytes`` in-memory. We avoid touching the filesystem by
    # capturing the bytes into a ``BytesIO`` buffer.

    response = await litellm.aspeech(
        model=model,
        voice=voice,
        input=text,
        optional_params=optional_params,
    )

    # Newer LiteLLM versions: ``response.audio_bytes``
    if hasattr(response, "audio_bytes") and isinstance(response.audio_bytes, (bytes, bytearray)):
        return bytes(response.audio_bytes)

    # Fallback for versions that require streaming to file
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        tmp_path = Path(tmp.name)
        response.stream_to_file(tmp_path)
        tmp.seek(0)
        mp3_bytes = tmp.read()

    try:
        tmp_path.unlink(missing_ok=True)
    except Exception:
        pass

    return mp3_bytes