"""Anthropic API failures must surface as clean, CORS-safe HTTP errors —
not as an unhandled 500 that browsers report as an opaque "Failed to fetch".
"""

import anthropic
import httpx
import pytest

from app.services.claude_client import call_structured_tool


def _make_status_error(cls, status_code: int, message: str):
    request = httpx.Request("POST", "https://api.anthropic.com/v1/messages")
    response = httpx.Response(status_code, request=request, json={"error": {"message": message}})
    return cls(message, response=response, body=None)


def test_authentication_error_becomes_401(monkeypatch):
    def raise_auth_error(*args, **kwargs):
        raise _make_status_error(anthropic.AuthenticationError, 401, "API key is invalid.")

    monkeypatch.setattr("app.services.claude_client.get_client", lambda: type(
        "FakeClient", (), {"messages": type("M", (), {"create": staticmethod(raise_auth_error)})()}
    )())

    with pytest.raises(Exception) as exc_info:
        call_structured_tool(
            system="sys",
            user_message="hi",
            tool_name="t",
            tool_description="d",
            input_schema={"type": "object", "properties": {}},
        )

    from fastapi import HTTPException

    assert isinstance(exc_info.value, HTTPException)
    assert exc_info.value.status_code == 401
    assert "rejected" in exc_info.value.detail.lower()


def test_job_creation_surfaces_clean_error_on_bad_key(client, monkeypatch):
    """End-to-end: a route that calls Claude should return a real HTTP error
    response (with a body FastAPI/Starlette will attach CORS headers to),
    not an unhandled exception.
    """

    def raise_auth_error(*args, **kwargs):
        raise _make_status_error(anthropic.AuthenticationError, 401, "API key is invalid.")

    monkeypatch.setattr("app.services.claude_client.get_client", lambda: type(
        "FakeClient", (), {"messages": type("M", (), {"create": staticmethod(raise_auth_error)})()}
    )())

    r = client.post("/api/jobs", json={"raw_text": "Some job posting..."})
    assert r.status_code == 401
    assert "rejected" in r.json()["detail"].lower()
