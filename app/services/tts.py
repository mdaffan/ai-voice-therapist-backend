"""Service – Text-to-speech helpers using OpenAI TTS models."""

from __future__ import annotations

import tempfile
from pathlib import Path
import asyncio
from openai import AsyncOpenAI
import requests

from app.infra.config import settings
from deepgram import (
    DeepgramClient,
    SpeakWebSocketEvents,
    SpeakWSOptions,
)

client = AsyncOpenAI(api_key=settings.openai_api_key)
# Deepgram client initialised lazily
deepgram: DeepgramClient | None = None


def _ensure_deepgram_client() -> DeepgramClient:
    """Return a singleton Deepgram client (initialise if needed)."""

    global deepgram
    if deepgram is None:
        deepgram = DeepgramClient(settings.deepgram_api_key)
    return deepgram


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
# Issues with streaming
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
    queue = asyncio.Queue()
    done = asyncio.Event()
    dg= _ensure_deepgram_client()
    dg_connection = dg.speak.websocket.v("1")
    def on_binary_data(self, data, **kwargs):
        try:
            print("Received binary data")
            queue.put_nowait(data) 
        except asyncio.QueueFull:
            pass  # drop or handle overflow if needed

    def on_close(self, *args, **kwargs):
        done.set()
    dg_connection.on(SpeakWebSocketEvents.AudioData, on_binary_data)
    dg_connection.on(SpeakWebSocketEvents.Close, on_close)
    options = SpeakWSOptions(
            model="aura-2-thalia-en",
            encoding="linear16",
            sample_rate=16000,
        )
    if dg_connection.start(options) is False:
        print("Failed to start connection")
        return
        # send the text to Deepgram
    dg_connection.send_text(text)
        # if auto_flush_speak_delta is not used, you must flush the connection by calling flush()
    dg_connection.flush()
    dg_connection.finish()
    while not done.is_set() or not queue.empty():
        chunk = await queue.get()
        print("Received chunk data", chunk)
        yield chunk 
   