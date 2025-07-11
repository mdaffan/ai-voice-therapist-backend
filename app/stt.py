"""STT placeholder.

Integrate Whisper (OpenAI or faster-whisper) later – this stub just returns
an empty string so the endpoint stays functional while you wire things up.
"""
import asyncio


async def transcribe_bytes(_: bytes) -> str:
    """Return a dummy transcription until STT is implemented."""
    # TODO: hook up Whisper or any STT service here
    return "" 