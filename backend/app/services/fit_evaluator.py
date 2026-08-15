"""Scores how well a job posting matches the user's real profile.

This never touches document generation — it's a read-only judgment call so
low-fit postings can be archived before any tailoring effort is spent on them.
"""

import json

from app.models import JobPosting, Profile
from app.services.claude_client import call_structured_tool

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
    return call_structured_tool(
        system=_SYSTEM,
        user_message=user_message,
        tool_name="record_fit_evaluation",
        tool_description="Record the fit evaluation between this candidate and this job posting.",
        input_schema=_SCHEMA,
        max_tokens=2048,
    )
