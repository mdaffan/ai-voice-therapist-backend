"""Service – Speech-to-text helper (Whisper)."""

import asyncio
from litellm import transcription
from deepgram import DeepgramClient, PrerecordedOptions
from app.infra.config import settings

import json

# Deepgram client initialised lazily
deepgram: DeepgramClient | None = None


def _ensure_deepgram_client() -> DeepgramClient:
    """Return a singleton Deepgram client (initialise if needed)."""

    global deepgram
    if deepgram is None:
        deepgram = DeepgramClient(settings.deepgram_api_key)
    return deepgram

async def transcribe_file(file_path: str, model: str = "whisper-1") -> str:
    """Transcribe an audio file already persisted on disk.

    If `settings.use_deepgram` is **truthy** and the Deepgram API key is set, the
    audio is sent to Deepgram; otherwise it falls back to OpenAI Whisper via
    `litellm.transcription`.
    """

    def _sync_run_deepgram() -> str:
        dg = _ensure_deepgram_client()
        with open(file_path, "rb") as buffer_data:
            payload = {"buffer": buffer_data}
            options = PrerecordedOptions(
                smart_format=True,
                model="nova-2",
                language="en-US",
            )
            response = dg.listen.prerecorded.v("1").transcribe_file(payload, options)
            dg_resp = json.loads(response.to_json(indent=4))
            return (
                dg_resp.get("results", {})
                .get("channels", [{}])[0]
                .get("alternatives", [{}])[0]
                .get("transcript", "")
            )

    def _sync_run_whisper() -> str:
        with open(file_path, "rb") as audio_file:
            resp = transcription(model=model, file=audio_file)
            return resp.get("text", "").strip()

    loop = asyncio.get_event_loop()

    if settings.use_deepgram and settings.deepgram_api_key:
        return await loop.run_in_executor(None, _sync_run_deepgram)
    else:
        return await loop.run_in_executor(None, _sync_run_whisper) 