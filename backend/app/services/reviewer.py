"""Reviewer agent: a second, independent pass over a Drafter's output.

This is a genuinely separate LLM call from the Drafter — not a second turn
in the same conversation, not the same prompt with an extra instruction
appended. It receives the draft and the real profile fresh, with no memory
of having written the draft itself, and its only job is to check: does
every claim in this draft trace back to something actually in the profile?
It flags problems; it does not silently rewrite anything. Silent "fixing"
would defeat the point of having an auditable second pass at all.
"""

import json

from app.models import JobPosting, Profile
from app.services.llm_client import call_structured_tool

_SYSTEM = (
    "You are a strict, independent reviewer checking a tailored resume and cover "
    "letter for a real job seeker. You did NOT write these documents. Your only job "
    "is to compare them against the candidate's real profile and the job posting, "
    "and flag problems — you never rewrite or silently fix anything yourself. "
    "Flag: (1) any claim, skill, metric, or achievement in the draft that is NOT "
    "clearly traceable to the profile — this is the most important check, treat it "
    "as fabrication even if it seems like a small embellishment; (2) important job "
    "keywords/requirements that the draft could have honestly included from the "
    "profile but didn't; (3) tone problems — generic corporate filler, or a voice "
    "that doesn't sound like a real person. Be specific: quote the exact phrase "
    "you're flagging."
)

_NOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "severity": {
            "type": "string",
            "enum": ["error", "warning", "info"],
            "description": (
                "error: likely fabrication, must be fixed before sending. "
                "warning: worth a second look (tone, missing keyword). "
                "info: minor/optional suggestion."
            ),
        },
        "message": {"type": "string", "description": "Specific, quoting the flagged text where possible."},
    },
    "required": ["severity", "message"],
}

_SCHEMA = {
    "type": "object",
    "properties": {
        "resume_passed": {
            "type": "boolean",
            "description": "False if any resume claim can't be traced to the profile (any 'error' severity note).",
        },
        "resume_notes": {"type": "array", "items": _NOTE_SCHEMA},
        "cover_letter_passed": {
            "type": "boolean",
            "description": "False if any cover letter claim can't be traced to the profile (any 'error' severity note).",
        },
        "cover_letter_notes": {"type": "array", "items": _NOTE_SCHEMA},
    },
    "required": ["resume_passed", "resume_notes", "cover_letter_passed", "cover_letter_notes"],
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


def review_documents(profile: Profile, job: JobPosting, draft: dict) -> dict:
    user_message = (
        f"CANDIDATE'S REAL PROFILE (the only source of truth — anything in the draft "
        f"that isn't grounded here is a fabrication, no matter how plausible it sounds):\n"
        f"{_profile_to_context(profile)}\n\n"
        f"JOB POSTING:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Requirements: {job.requirements}\n"
        f"Keywords: {job.keywords}\n\n"
        f"DRAFT RESUME to review:\n{json.dumps(draft.get('resume', {}), indent=2)}\n\n"
        f"DRAFT COVER LETTER to review:\n{json.dumps(draft.get('cover_letter', {}), indent=2)}\n\n"
        f"Review both documents now."
    )
    return call_structured_tool(
        system=_SYSTEM,
        user_message=user_message,
        tool_name="record_review",
        tool_description="Record the review findings for this draft.",
        input_schema=_SCHEMA,
        max_tokens=2048,
    )
