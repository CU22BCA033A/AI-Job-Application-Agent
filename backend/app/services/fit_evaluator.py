"""Scores how well a job posting matches the user's real profile.

This never touches document generation — it's a read-only judgment call so
low-fit postings can be archived before any tailoring effort is spent on them.

The score is a blend of two genuinely different signals:

- A deterministic keyword match (this file, no LLM) — the same surface-level
  "does this exact term appear anywhere in the profile" check a real ATS
  keyword scanner does against the job's extracted requirements/keywords.
  Grounded, reproducible, and exactly why the number moves when you change
  your profile or the posting.
- The LLM's holistic read of the two (services/fit_evaluator's
  `_SYSTEM`/`_SCHEMA` below) — catches things pure keyword matching can't:
  synonyms, seniority fit, transferable experience described differently
  than the posting's wording.

Keyword match is weighted more heavily (65/35) since "acts like an ATS" is
the explicit goal here, and a black-box LLM number alone was the original
complaint — this makes the score demonstrably traceable to the actual
posting text, not just a model's vibes.
"""

import json
import re

from app.models import JobPosting, Profile
from app.services.llm_client import call_structured_tool

_SYSTEM = (
    "You are a candid, experienced career coach evaluating fit between a real "
    "candidate profile and a job posting. Be honest, not encouraging-by-default — "
    "a low score with clear reasoning is more useful than false optimism. "
    "Base strengths and gaps ONLY on what's actually in the candidate profile; "
    "never assume skills or experience that aren't listed."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "fit_score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Overall fit, 0-100.",
        },
        "strengths": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Specific ways the candidate's real experience matches this posting.",
        },
        "gaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Real, honest gaps between the posting's requirements and the profile.",
        },
        "reasoning": {
            "type": "string",
            "description": "2-4 sentence explanation of the score, in a direct, human tone.",
        },
        "recommendation": {
            "type": "string",
            "enum": ["tailor_and_apply", "stretch_tailor_carefully", "skip"],
            "description": (
                "tailor_and_apply: strong match, worth tailoring now. "
                "stretch_tailor_carefully: plausible but has real gaps, tailor with care. "
                "skip: not worth the effort, gaps are too large or role is misaligned."
            ),
        },
    },
    "required": ["fit_score", "strengths", "gaps", "reasoning", "recommendation"],
}

_KEYWORD_WEIGHT = 0.65
_LLM_WEIGHT = 0.35


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()


def _profile_searchable_text(profile: Profile) -> str:
    parts: list[str] = [profile.summary]
    for role in profile.work_history or []:
        parts.append(role.get("title", ""))
        parts.extend(role.get("bullets", []) or [])
        parts.extend(role.get("skills_used", []) or [])
    for skill in profile.skills or []:
        parts.append(skill.get("name", ""))
    for project in profile.projects or []:
        parts.append(project.get("name", ""))
        parts.extend(project.get("bullets", []) or [])
        parts.extend(project.get("technologies", []) or [])
    for achievement in profile.achievements or []:
        parts.append(achievement.get("title", ""))
        parts.append(achievement.get("description", ""))
    for edu in profile.education or []:
        parts.append(edu.get("degree", ""))
        parts.append(edu.get("field", ""))
    return _normalize(" ".join(p for p in parts if p))


def keyword_match(job: JobPosting, profile: Profile) -> dict:
    """Surface-level "does this term appear in the profile" match, the same
    blunt-but-real technique an actual ATS keyword scanner uses. Terms come
    from the job's already-extracted keywords/requirements (job intake), so
    this reflects the specific posting, not a generic skills list.
    """
    haystack = _profile_searchable_text(profile)
    seen: set[str] = set()
    candidates: list[str] = []
    for term in [*(job.keywords or []), *(job.requirements or [])]:
        norm = _normalize(term)
        if len(norm) < 2 or norm in seen:
            continue
        seen.add(norm)
        candidates.append(term)

    matched, missing = [], []
    for term in candidates:
        if _normalize(term) in haystack:
            matched.append(term)
        else:
            missing.append(term)

    total = len(matched) + len(missing)
    score = round(100 * len(matched) / total) if total else None
    return {"score": score, "matched": matched, "missing": missing}


def _profile_to_context(profile: Profile) -> str:
    return json.dumps(
        {
            "summary": profile.summary,
            "work_history": profile.work_history,
            "education": profile.education,
            "skills": profile.skills,
            "projects": profile.projects,
            "achievements": profile.achievements,
        },
        indent=2,
    )


def evaluate_fit(profile: Profile, job: JobPosting) -> dict:
    user_message = (
        f"CANDIDATE PROFILE (the only source of truth about this person):\n"
        f"{_profile_to_context(profile)}\n\n"
        f"JOB POSTING:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Requirements: {job.requirements}\n"
        f"Keywords: {job.keywords}\n\n"
        f"Full posting text:\n{job.raw_text}"
    )
    llm_result = call_structured_tool(
        system=_SYSTEM,
        user_message=user_message,
        tool_name="record_fit_evaluation",
        tool_description="Record the fit evaluation between this candidate and this job posting.",
        input_schema=_SCHEMA,
        max_tokens=2048,
    )

    analysis = keyword_match(job, profile)
    if analysis["score"] is None:
        # Posting had no extractable keywords/requirements to check against —
        # fall back to the LLM's holistic score alone rather than blending
        # against a meaningless 0.
        blended_score = llm_result["fit_score"]
    else:
        blended_score = round(_KEYWORD_WEIGHT * analysis["score"] + _LLM_WEIGHT * llm_result["fit_score"])

    llm_result["fit_score"] = max(0, min(100, blended_score))
    llm_result["keyword_analysis"] = analysis
    return llm_result
