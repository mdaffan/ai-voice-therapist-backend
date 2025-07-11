"""Chat completion via LiteLLM Router (GPT-4o primary, Claude Opus fallback)."""
import asyncio
import os
from litellm import Router

_model_list = [
    {"model_name": "primary", "litellm_params": {"model": "gpt-4o"}},
    {
        "model_name": "fallback",
        "litellm_params": {"model": "anthropic/claude-3-opus"},
    },
]

_router = Router(
    model_list=_model_list,
    fallbacks=[{"primary": ["fallback"]}],
    routing_strategy="latency-based-routing",
    cache_responses=True,
)


async def generate(prompt: str) -> str:
    """Return assistant reply as plain text."""
    response = await _router.acompletion(
        model="primary",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        stream=False,
    )
    return response.choices[0].message.content.strip() 