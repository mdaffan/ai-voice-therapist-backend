"""Service – chat completion via LiteLLM Router (GPT-4o primary, Claude fallback)."""

from __future__ import annotations

from litellm.router import Router

# Therapist prompt kept close to the service so routers can import it.
THERAPIST_SYSTEM_PROMPT = """
You are "Voice Therapist", a voice-based mental health agent speaking gently and naturally in short, human-like replies. You help users feel safe, heard, and guided using voice-first conversation.

# Personality & Style
- Speak as if you’re on a voice call: natural, calm, brief.
- Use **active listening** (acknowledge, validate, gently guide).
- Avoid long or complex sentences – this will be read aloud.
- Pause to let the user speak again. Never overload.

# Cultural Sensitivity
- Respect Islamic values, family roles, and Omani social norms.
- Avoid slang or Western metaphors.
- Encourage family support or spiritual reflection when appropriate.

# Clinical Boundaries
- You are NOT a doctor. Never give diagnoses or prescriptions.
- For serious issues, suggest speaking to a licensed therapist.

# Crisis Protocol
If the user expresses suicidal thoughts, harm, or danger:
- Say calmly: “I hear how hard this is. Please, speak to someone now.”
- Suggest local hotline or emergency services.
- Stop therapeutic dialogue immediately.

# Output Format
Always reply in natural spoken tone. Limit to 1–2 short sentences, ~75 words max.

---
Begin the session warm and gentle:
“Hi, I’m here for you. How are you feeling today?”
"""

_model_list = [
    {"model_name": "primary", "litellm_params": {"model": "gpt-4o"}},
    {
        "model_name": "fallback",
        "litellm_params": {"model": "anthropic/claude-3-7-sonnet-latest"},
    },
]

_router = Router(
    model_list=_model_list,
    fallbacks=[{"primary": ["fallback"]}],
    # routing_strategy="latency-based-routing", Can be used to route to the fastest model, we can even use least busy, etc
    # mock_testing_fallbacks=True, For testing purposes, we can mock the fallback model
)


async def generate(messages: list[dict], *, temperature: float = 0.7) -> str | None:
    """Return assistant reply as plain text, given full message history."""
    response = await _router.acompletion(
        model="primary",
        messages=messages,
        temperature=temperature,
        stream=False,
    )
    return response.choices[0].message.content


async def generate_stream(messages: list[dict], *, temperature: float = 0.7):
    """Yield assistant reply chunks as they arrive (SSE-friendly)."""

    stream = await _router.acompletion(
        model="primary",
        messages=messages,
        temperature=temperature,
        stream=True,
    )

    async for chunk in stream:
        delta = chunk.choices[0].delta
        content_piece = (
            delta.get("content") if isinstance(delta, dict) else getattr(delta, "content", "")
        )
        if content_piece:
            yield content_piece 