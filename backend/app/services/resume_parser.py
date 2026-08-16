"""Parses a pasted-in resume (plain text, extracted from PDF or typed) into the
structured Profile shape, for the user to review and correct — never trusted blindly.
"""

import logging

from fastapi import HTTPException

from app.config import get_settings
from app.services.llm_client import call_structured_tool

settings = get_settings()
logger = logging.getLogger("vrutti")

_SYSTEM = (
    "You convert a resume's raw text into a structured profile record. Your #1 "
    "failure mode is being lazy: leaving work_history, skills, or projects empty "
    "or thin when the resume text clearly lists them. Before you finish, re-scan "
    "the ENTIRE text for every section — a 'Skills' or 'Technical Skills' line "
    "(often a dense comma/pipe-separated list of tools, languages, and "
    "frameworks — split each one into its own skills[] entry), every internship "
    "or work entry (even short/unpaid ones), every project with its own bullets, "
    "and any tools/technologies named inside bullet points that aren't already "
    "in the skills list. A resume that lists tools is not a resume with no "
    "skills — extract every single one you can find as its own entry. "
    "That said, extract only what is actually written — do not infer skills, "
    "dates, or achievements that aren't stated. If a field is unclear or "
    "missing, leave it empty and add a short note about it so the person can "
    "fill it in themselves. Preserve real numbers/metrics exactly as written; "
    "never round or embellish them."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": "string"},
        "email": {"type": "string"},
        "phone": {"type": "string"},
        "location": {"type": "string"},
        "links": {
            "type": "object",
            "additionalProperties": {"type": "string"},
            "description": "e.g. {\"linkedin\": \"...\", \"github\": \"...\", \"portfolio\": \"...\"}",
        },
        "summary": {"type": "string", "description": "Existing summary/objective, if present, verbatim."},
        "work_history": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "location": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "current": {"type": "boolean"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "skills_used": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["company", "title", "bullets"],
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "institution": {"type": "string"},
                    "degree": {"type": "string"},
                    "field": {"type": "string"},
                    "start_date": {"type": "string"},
                    "end_date": {"type": "string"},
                    "gpa": {"type": "string"},
                    "notes": {"type": "string"},
                },
                "required": ["institution"],
            },
        },
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "proficiency": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                    "technologies": {"type": "array", "items": {"type": "string"}},
                    "url": {"type": "string"},
                },
                "required": ["name"],
            },
        },
        "achievements": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "metric": {"type": "string"},
                    "date": {"type": "string"},
                },
                "required": ["title"],
            },
        },
        "parsing_notes": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Anything ambiguous, missing, or worth double-checking manually.",
        },
    },
    "required": [
        "full_name",
        "email",
        "phone",
        "location",
        "links",
        "summary",
        "work_history",
        "education",
        "skills",
        "projects",
        "achievements",
        "parsing_notes",
    ],
}


_SKILLS_SYSTEM = (
    "You extract a flat list of every skill, tool, technology, programming "
    "language, framework, platform, or methodology mentioned ANYWHERE in this "
    "resume text — not just in a labeled 'Skills' section. Check every "
    "section: a 'Skills'/'Technical Skills' block (often several dense "
    "comma- or pipe-separated lines — split EVERY item into its own entry, "
    "however many there are, don't sample a few and stop), every work "
    "experience bullet, every project description, and every certification. "
    "List every distinct item you find, even if that's 30+ entries — do not "
    "summarize or pick representative examples. Extract only what is "
    "actually written; never infer a skill that isn't named."
)

_SKILLS_SCHEMA = {
    "type": "object",
    "properties": {
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "category": {"type": "string"},
                    "proficiency": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    "required": ["skills"],
}


def _extract_skills(resume_text: str) -> list[dict]:
    """A dense "Skills:" list is easy for a model to skim rather than fully
    transcribe inside one giant multi-section extraction — this is a small,
    single-purpose call for just that one task, which is far more reliable
    at it than the main pass in practice. Best-effort: any failure here
    (rate limit, timeout, malformed output) degrades to "found nothing
    extra" rather than failing the whole import over an enhancement step.
    """
    try:
        result = call_structured_tool(
            system=_SKILLS_SYSTEM,
            user_message=f"Resume text:\n\n{resume_text}",
            tool_name="record_skills",
            tool_description="Record every skill/tool/technology found in this resume.",
            input_schema=_SKILLS_SCHEMA,
            max_tokens=4096,
            model=settings.nvidia_model_resume_parse,
        )
        return result.get("skills", [])
    except HTTPException:
        logger.warning("Supplemental skills extraction failed; continuing with the main pass's skills only.")
        return []


def _merge_skills(primary: list[dict], supplemental: list[dict]) -> list[dict]:
    merged = list(primary)
    seen = {s.get("name", "").strip().lower() for s in primary if s.get("name")}
    for skill in supplemental:
        key = skill.get("name", "").strip().lower()
        if key and key not in seen:
            seen.add(key)
            merged.append(skill)
    return merged


def parse_resume_text(resume_text: str) -> dict:
    result = call_structured_tool(
        system=_SYSTEM,
        user_message=f"Resume text:\n\n{resume_text}",
        tool_name="record_parsed_profile",
        tool_description="Record the structured profile parsed from this resume.",
        input_schema=_SCHEMA,
        max_tokens=8192,
        # Runs once per profile import, not per request, so it can afford a
        # larger/slower model than the app's default even when NVIDIA_MODEL
        # is set to something fast — see the field's docstring in config.py.
        model=settings.nvidia_model_resume_parse,
    )
    result["skills"] = _merge_skills(result.get("skills", []), _extract_skills(resume_text))
    return result
