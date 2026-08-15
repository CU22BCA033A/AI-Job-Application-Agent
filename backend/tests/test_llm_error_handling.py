"""LLM provider (NVIDIA NIM) failures must surface as clean, CORS-safe HTTP
errors — not as an unhandled 500 that browsers report as an opaque
"Failed to fetch".
"""

import json

import httpx
import openai
import pytest

from app.services.llm_client import call_structured_tool


def _make_status_error(cls, status_code: int, message: str):
    request = httpx.Request("POST", "https://integrate.api.nvidia.com/v1/chat/completions")
    response = httpx.Response(status_code, request=request, json={"error": {"message": message}})
    return cls(message, response=response, body=None)


def _fake_client_raising(exc: Exception):
    def raise_error(*args, **kwargs):
        raise exc

    return type(
        "FakeClient", (), {"chat": type("C", (), {"completions": type("M", (), {"create": staticmethod(raise_error)})()})()}
    )()


def test_authentication_error_becomes_401(monkeypatch):
    exc = _make_status_error(openai.AuthenticationError, 401, "Invalid API key")
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: _fake_client_raising(exc))

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
    """End-to-end: a route that calls the LLM should return a real HTTP error
    response (with a body FastAPI/Starlette will attach CORS headers to),
    not an unhandled exception.
    """
    exc = _make_status_error(openai.AuthenticationError, 401, "Invalid API key")
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: _fake_client_raising(exc))

    r = client.post("/api/jobs", json={"raw_text": "Some job posting..."})
    assert r.status_code == 401
    assert "rejected" in r.json()["detail"].lower()


def _fake_tool_call_response(tool_name: str, arguments: dict):
    function = type("F", (), {"name": tool_name, "arguments": json.dumps(arguments)})()
    tool_call = type("TC", (), {"function": function})()
    message = type("Msg", (), {"tool_calls": [tool_call]})()
    choice = type("Choice", (), {"message": message})()
    return type("Resp", (), {"choices": [choice]})()


def test_missing_tool_call_becomes_502(monkeypatch):
    """Some open models ignore a forced tool_choice — that must surface as a
    clear error, not silently return an empty/garbage dict.
    """
    message = type("Msg", (), {"tool_calls": []})()
    choice = type("Choice", (), {"message": message})()
    response = type("Resp", (), {"choices": [choice]})()

    def fake_create(*args, **kwargs):
        return response

    fake_client = type(
        "FakeClient", (), {"chat": type("C", (), {"completions": type("M", (), {"create": staticmethod(fake_create)})()})()}
    )()
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: fake_client)

    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc_info:
        call_structured_tool(
            system="sys",
            user_message="hi",
            tool_name="record_thing",
            tool_description="d",
            input_schema={"type": "object", "properties": {}},
        )

    assert exc_info.value.status_code == 502
    assert "record_thing" in exc_info.value.detail


def test_successful_tool_call_parses_arguments(monkeypatch):
    response = _fake_tool_call_response("record_thing", {"score": 88})

    def fake_create(*args, **kwargs):
        return response

    fake_client = type(
        "FakeClient", (), {"chat": type("C", (), {"completions": type("M", (), {"create": staticmethod(fake_create)})()})()}
    )()
    monkeypatch.setattr("app.services.llm_client.get_client", lambda: fake_client)

    result = call_structured_tool(
        system="sys",
        user_message="hi",
        tool_name="record_thing",
        tool_description="d",
        input_schema={"type": "object", "properties": {"score": {"type": "integer"}}},
    )
    assert result == {"score": 88}
