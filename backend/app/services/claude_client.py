"""Thin wrapper around the Anthropic Messages API for structured (tool-call) outputs.

Every agent in this app (extraction, fit evaluator, drafter, reviewer) asks
Claude to call a single tool whose input schema is the shape we want back —
this keeps outputs typed and avoids fragile prose parsing.
"""

from typing import Any

import anthropic

from app.config import get_settings

settings = get_settings()

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        if not settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY is not set. Copy backend/.env.example to backend/.env "
                "and add your key from https://console.anthropic.com/"
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

    Raises RuntimeError if Claude doesn't use the tool (shouldn't happen with
    tool_choice pinned, but we fail loudly rather than silently returning {}).
    """
    client = get_client()
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

    for block in response.content:
        if block.type == "tool_use" and block.name == tool_name:
            return block.input

    raise RuntimeError(f"Claude did not return a '{tool_name}' tool call as expected.")
