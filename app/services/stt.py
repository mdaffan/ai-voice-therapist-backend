"""Service – Speech-to-text helper (Whisper)."""

import asyncio
from litellm import transcription


async def transcribe_file(file_path: str, model: str = "whisper-1") -> str:
    """Transcribe an audio file already persisted on disk."""

    def _sync_run() -> str:
        with open(file_path, "rb") as audio_file:
            response = transcription(model=model, file=audio_file)
            return response.get("text", "").strip()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_run) 