"""Thin wrapper around the Anthropic Messages API for structured (tool-call) outputs.

Every agent in this app (extraction, fit evaluator, drafter, reviewer) asks
Claude to call a single tool whose input schema is the shape we want back —
this keeps outputs typed and avoids fragile prose parsing.
"""

from typing import Any

import anthropic
from fastapi import HTTPException

from app.config import get_settings

settings = get_settings()

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise HTTPException(
                status_code=500,
                detail=(
                    "ANTHROPIC_API_KEY is not set on the server. Copy backend/.env.example to "
                    "backend/.env (or set it in your deployment's environment variables) and "
                    "add your key from https://console.anthropic.com/"
                ),
            )
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
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
    """Force Claude to respond via a single tool call and return its input dict.

    Anthropic API failures (bad key, rate limit, network, upstream error) are
    translated into clean HTTPExceptions here — so a Claude-side failure
    surfaces to the UI as a readable message instead of an opaque 500 whose
    error response is missing CORS headers and shows up in the browser as a
    generic, undiagnosable "Failed to fetch".
    """
    client = get_client()

    try:
        response = client.messages.create(
            model=settings.claude_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
            tools=[
                {
                    "name": tool_name,
                    "description": tool_description,
                    "input_schema": input_schema,
                }
            ],
            tool_choice={"type": "tool", "name": tool_name},
        )
    except anthropic.AuthenticationError as exc:
        raise HTTPException(
            status_code=401,
            detail="Your Anthropic API key was rejected. Double-check ANTHROPIC_API_KEY.",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=429,
            detail="Hit the Anthropic rate limit — wait a moment and try again.",
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(
            status_code=502,
            detail="Couldn't reach the Anthropic API. Check your network and try again.",
        ) from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(status_code=502, detail=f"Claude API error: {exc.message}") from exc

    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input

    raise HTTPException(
        status_code=502,
        detail=f"Claude didn't return the expected '{tool_name}' response — try again.",
    )
