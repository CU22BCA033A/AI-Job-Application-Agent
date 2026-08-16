"""Resume parsing must use the (separately configurable) resume-parsing
model, not whatever fast/small model NVIDIA_MODEL is set to for
latency-sensitive calls — a large nested extraction schema is a much
harder one-shot task than a quick fit score.
"""

from app.services.resume_parser import parse_resume_text


def test_parse_resume_text_uses_the_resume_parse_model(monkeypatch):
    monkeypatch.setattr("app.services.resume_parser.settings.nvidia_model", "meta/llama-3.1-8b-instruct")
    monkeypatch.setattr(
        "app.services.resume_parser.settings.nvidia_model_resume_parse", "meta/llama-3.3-70b-instruct"
    )

    captured = {}

    def fake_call_structured_tool(**kwargs):
        captured.update(kwargs)
        return {
            "full_name": "",
            "email": "",
            "phone": "",
            "location": "",
            "links": {},
            "summary": "",
            "work_history": [],
            "education": [],
            "skills": [],
            "projects": [],
            "achievements": [],
            "parsing_notes": [],
        }

    monkeypatch.setattr("app.services.resume_parser.call_structured_tool", fake_call_structured_tool)

    parse_resume_text("some resume text")

    assert captured["model"] == "meta/llama-3.3-70b-instruct"
