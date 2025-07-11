"""Text-to-speech using LiteLLM TTS."""
import asyncio
import litellm

# You can set your provider/model/voice via environment variables or directly in the function call
# See: https://docs.litellm.ai/docs/text_to_speech#quick-start

async def synthesize(text: str) -> bytes:
    response = await litellm.atext_to_speech(
        input=text,
        model="tts-1",  # or your preferred TTS model
        voice="alloy",  # or your preferred voice
        response_format="mp3"
    )
    return response  # This is the raw audio bytes 