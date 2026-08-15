"""Thin wrapper around an OpenAI-compatible chat completions API for
structured (forced function-call) outputs.

Backed by NVIDIA NIM (build.nvidia.com) by default — a free-tier inference
endpoint that speaks the OpenAI API shape. Every agent in this app
(extraction, fit evaluator, drafter, reviewer) asks the model to call a
single function whose parameters schema is the shape we want back, via a
forced `tool_choice` — this keeps outputs typed and avoids fragile prose
parsing, the same way the app was originally built against Anthropic's
Messages API tool-use.

Caveat worth knowing: tool-calling reliability varies by open model. If
NVIDIA_MODEL doesn't support forced function calling well, responses may
omit the tool call entirely — handled below as a clear error rather than a
silent empty result.
"""

import json
from typing import Any

import openai
from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()

_client: openai.OpenAI | None = None


def get_client() -> openai.OpenAI:
    global _client
    if _client is None:
        if not settings.nvidia_api_key:
            raise HTTPException(
                status_code=500,
                detail=(
                    "NVIDIA_API_KEY is not set on the server. Copy backend/.env.example to "
                    "backend/.env (or set it in your deployment's environment variables) and "
                    "add a free key from https://build.nvidia.com/"
                ),
            )
        _client = openai.OpenAI(base_url=settings.nvidia_base_url, api_key=settings.nvidia_api_key)
    return _client


def call_structured_tool(
    *,
    system: str,
    user_message: str,
    tool_name: str,
    tool_description: str,
    input_schema: dict[str, Any],
    max_tokens: int = 4096,
) -> dict[str, Any]:
    """Force the model to respond via a single function call and return its
    parsed arguments dict.

    Provider failures (bad key, rate limit, network, upstream error) are
    translated into clean HTTPExceptions here — so an LLM-side failure
    surfaces to the UI as a readable message instead of an opaque 500 whose
    error response is missing CORS headers and shows up in the browser as a
    generic, undiagnosable "Failed to fetch".
    """
    client = get_client()

    try:
        response = client.chat.completions.create(
            model=settings.nvidia_model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user_message},
            ],
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": tool_name,
                        "description": tool_description,
                        "parameters": input_schema,
                    },
                }
            ],
            tool_choice={"type": "function", "function": {"name": tool_name}},
        )
    except openai.AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail="Your NVIDIA API key was rejected. Double-check NVIDIA_API_KEY.",
        ) from exc
    except openai.RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Hit the NVIDIA NIM rate limit — wait a moment and try again.",
        ) from exc
    except openai.APIConnectionError as exc:
        raise HTTPException(
            status_code=502,
            detail="Couldn't reach the NVIDIA API. Check your network and try again.",
        ) from exc
    except openai.APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"NVIDIA API error: {exc.message}") from exc

    message = response.choices[0].message
    tool_calls = message.tool_calls or []

    for call in tool_calls:
        if call.function.name == tool_name:
            try:
                return json.loads(call.function.arguments)
            except json.JSONDecodeError as exc:
                raise HTTPException(
                    status_code=502,
                    detail="The model returned malformed structured output — try again.",
                ) from exc

    raise HTTPException(
        status_code=502,
        detail=(
            f"The model didn't return the expected '{tool_name}' response — try again, "
            "or set NVIDIA_MODEL to a model with reliable tool-calling support."
        ),
    )
