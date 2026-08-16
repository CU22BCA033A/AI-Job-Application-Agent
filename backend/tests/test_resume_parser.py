"""Resume parsing must use the (separately configurable) resume-parsing
model, not whatever fast/small model NVIDIA_MODEL is set to for
latency-sensitive calls — a large nested extraction schema is a much
harder one-shot task than a quick fit score. It also runs a dedicated
second call just for skills, since a dense "Skills:" list is the most
commonly under-extracted part of the single big pass, and merges the
result in rather than trusting either call alone.
"""

from fastapi import HTTPException

from app.services.resume_parser import parse_resume_text

def _base_parse_result() -> dict:
    # A fresh dict every call — parse_resume_text() mutates result["skills"]
    # in place, so a shared module-level dict would leak state between tests.
    return {
        "full_name": "Jordan Lee",
        "email": "jordan@example.com",
        "phone": "",
        "location": "",
        "links": {},
        "summary": "",
        "work_history": [],
        "education": [],
        "skills": [{"name": "Python"}],
        "projects": [],
        "achievements": [],
        "parsing_notes": [],
    }


def _dispatch_by_tool_name(main_result: dict, skills_result: list[dict]):
    def fake_call_structured_tool(*, tool_name, **kwargs):
        if tool_name == "record_parsed_profile":
            return main_result
        if tool_name == "record_skills":
            return {"skills": skills_result}
        raise AssertionError(f"unexpected tool_name {tool_name}")

    return fake_call_structured_tool


def test_parse_resume_text_uses_the_resume_parse_model(monkeypatch):
    monkeypatch.setattr("app.services.resume_parser.settings.nvidia_model", "meta/llama-3.1-8b-instruct")
    monkeypatch.setattr(
        "app.services.resume_parser.settings.nvidia_model_resume_parse", "meta/llama-3.3-70b-instruct"
    )

    captured_models = []

    def fake_call_structured_tool(*, model, tool_name, **kwargs):
        captured_models.append(model)
        if tool_name == "record_parsed_profile":
            return _base_parse_result()
        return {"skills": []}

    monkeypatch.setattr("app.services.resume_parser.call_structured_tool", fake_call_structured_tool)

    parse_resume_text("some resume text")

    # Both the main parse and the supplemental skills call use the
    # resume-parse model, never the (possibly smaller/faster) default.
    assert captured_models == ["meta/llama-3.3-70b-instruct", "meta/llama-3.3-70b-instruct"]


def test_supplemental_skills_are_merged_in_without_duplicating(monkeypatch):
    monkeypatch.setattr(
        "app.services.resume_parser.call_structured_tool",
        _dispatch_by_tool_name(
            _base_parse_result(),
            [{"name": "Python"}, {"name": "Burp Suite"}, {"name": "Nmap"}],
        ),
    )

    result = parse_resume_text("some resume text")

    names = {s["name"] for s in result["skills"]}
    assert names == {"Python", "Burp Suite", "Nmap"}  # Python not duplicated
    assert len(result["skills"]) == 3


def test_supplemental_skills_call_failing_does_not_break_the_import(monkeypatch):
    def fake_call_structured_tool(*, tool_name, **kwargs):
        if tool_name == "record_parsed_profile":
            return _base_parse_result()
        raise HTTPException(status_code=429, detail="rate limited")

    monkeypatch.setattr("app.services.resume_parser.call_structured_tool", fake_call_structured_tool)

    result = parse_resume_text("some resume text")

    # Degrades to whatever the main pass already found, not an exception.
    assert result["skills"] == [{"name": "Python"}]
