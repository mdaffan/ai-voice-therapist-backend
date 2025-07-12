"""STT placeholder.

Integrate Whisper (OpenAI or faster-whisper) later – this stub just returns
an empty string so the endpoint stays functional while you wire things up.
"""
import asyncio

from litellm import transcription
import os 





# New helper that works with a file path on disk (used by main.py)
async def transcribe_file(file_path: str) -> str:
    """Transcribe an audio file already persisted on disk (placeholder)."""

    def _sync_run() -> str:
        with open(file_path, "rb") as audio_file:
            response = transcription(model="gpt-4o-transcribe", file=audio_file)
            # Adapt this depending on your provider’s response schema
            return response.get("text", "").strip()

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_run) 