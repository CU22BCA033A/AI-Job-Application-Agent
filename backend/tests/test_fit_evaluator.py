"""Unit tests for the deterministic ATS-style keyword match and how it
blends with the LLM's holistic score — the part of fit evaluation that
doesn't depend on any model call.
"""

from app.models import JobPosting, Profile
from app.services.fit_evaluator import evaluate_fit, keyword_match


def _profile(**overrides) -> Profile:
    defaults = dict(
        summary="Backend engineer focused on distributed systems.",
        work_history=[
            {
                "company": "Fintrust",
                "title": "Senior Backend Engineer",
                "bullets": ["Cut p99 latency 42% by redesigning the payments queue with Kafka."],
                "skills_used": ["Python", "Kafka", "PostgreSQL"],
            }
        ],
        education=[],
        skills=[{"name": "Python"}, {"name": "Kafka"}, {"name": "PostgreSQL"}],
        projects=[],
        achievements=[],
    )
    defaults.update(overrides)
    return Profile(**defaults)


def _job(**overrides) -> JobPosting:
    defaults = dict(
        raw_text="...",
        requirements=["5+ years backend experience", "Kafka", "PostgreSQL"],
        keywords=["Python", "Kafka", "PostgreSQL", "distributed systems"],
    )
    defaults.update(overrides)
    return JobPosting(**defaults)


def test_keyword_match_finds_terms_present_in_profile():
    result = keyword_match(_job(), _profile())
    assert "Python" in result["matched"]
    assert "Kafka" in result["matched"]
    assert "PostgreSQL" in result["matched"]
    assert "distributed systems" in result["matched"]  # appears in the summary text
    # "5+ years backend experience" legitimately isn't literal profile text —
    # that's the one genuinely missing term out of five candidates.
    assert result["missing"] == ["5+ years backend experience"]
    assert result["score"] == 80


def test_keyword_match_flags_genuinely_missing_terms():
    profile = _profile(
        skills=[{"name": "Ruby"}],
        work_history=[],
        summary="Backend engineer.",
    )
    result = keyword_match(_job(), profile)
    assert "Kafka" in result["missing"]
    assert "PostgreSQL" in result["missing"]
    assert result["score"] < 50


def test_keyword_match_is_case_and_punctuation_insensitive():
    profile = _profile(skills=[{"name": "postgresql"}], work_history=[], summary="node.js and react.js")
    job = _job(requirements=[], keywords=["PostgreSQL", "React.js"])
    result = keyword_match(job, profile)
    assert set(result["matched"]) == {"PostgreSQL", "React.js"}


def test_keyword_match_deduplicates_terms_appearing_in_both_lists():
    job = _job(requirements=["Kafka"], keywords=["Kafka"])
    result = keyword_match(job, _profile())
    assert result["matched"].count("Kafka") == 1


def test_keyword_match_returns_none_score_when_no_terms_to_check():
    job = _job(requirements=[], keywords=[])
    result = keyword_match(job, _profile())
    assert result["score"] is None
    assert result["matched"] == []
    assert result["missing"] == []


def test_evaluate_fit_blends_keyword_and_llm_scores(monkeypatch):
    """The whole point of the blend: a keyword-light profile should pull the
    final score down even if the LLM alone is generous, and vice versa.
    """
    monkeypatch.setattr(
        "app.services.fit_evaluator.call_structured_tool",
        lambda **kwargs: {
            "fit_score": 90,
            "strengths": ["..."],
            "gaps": [],
            "reasoning": "...",
            "recommendation": "tailor_and_apply",
        },
    )
    weak_profile = _profile(skills=[], work_history=[], summary="")
    result = evaluate_fit(weak_profile, _job())

    # keyword score is 0 here (nothing matches), LLM said 90 -> blend pulls it well below 90
    assert result["fit_score"] < 90
    assert result["keyword_analysis"]["score"] == 0


def test_evaluate_fit_falls_back_to_llm_score_when_no_keywords(monkeypatch):
    monkeypatch.setattr(
        "app.services.fit_evaluator.call_structured_tool",
        lambda **kwargs: {
            "fit_score": 61,
            "strengths": [],
            "gaps": [],
            "reasoning": "...",
            "recommendation": "stretch_tailor_carefully",
        },
    )
    job = _job(requirements=[], keywords=[])
    result = evaluate_fit(_profile(), job)
    assert result["fit_score"] == 61
    assert result["keyword_analysis"]["score"] is None
