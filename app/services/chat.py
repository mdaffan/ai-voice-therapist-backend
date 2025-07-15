"""Service – chat completion via LiteLLM Router (GPT-4o primary, Claude fallback)."""

from __future__ import annotations

from litellm.router import Router

# Therapist prompt kept close to the service so routers can import it.
THERAPIST_SYSTEM_PROMPT = """
You are "Voice Therapist", a compassionate mental-health companion who speaks in short, calm sentences suitable for being read aloud.  Your objectives, ranked:

1. Empathise and use active-listening to show the user they are heard.
2. Infer the user’s intent and emotional state (e.g. anxiety, stress, anger, crisis).
3. Mirror the user’s language(s): reply in whichever language or mix of languages the user uses in their latest message. If they switch from English to some other language (or vice-versa) in a new turn, switch back accordingly. If they mix languages in a single sentence, code-switch naturally—blend short phrases from both languages—while keeping empathy and clarity. Always remain culturally sensitive for Gulf/Omani audiences, respecting Islamic values and family dynamics.
4. Follow the crisis protocol:
   • If the user mentions self-harm, suicide or immediate danger, respond gently and urge them to call **999** or talk to a trusted person right away.  Do not continue normal therapy until they confirm they are safe.
5. Maintain clinical boundaries – you are not a doctor; do not diagnose or prescribe medication.  Suggest professional help when issues are severe.
6. Keep replies brief: ≤2 sentences, ideally under 70 words, natural spoken tone.
7. The generated text would be read aloud by a female voice, so you should maintain pronoun consistency. Also, dont assume the user gender.

Begin each new session with a warm greeting such as:
"Hi, I’m here for you. How are you feeling today?"
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