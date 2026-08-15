"""Generates a likely interview question bank and a STAR-format story bank
for a specific job, built only from the candidate's real achievements.

Same anti-fabrication rule as the Drafter: every story must be traceable to
something in the profile. This agent doesn't get a separate Reviewer pass —
it's lower-stakes than a document you submit to an employer (nothing here
leaves your machine unless you choose to use it in an interview), so the
guardrail is the prompt itself plus your own judgment reading it.
"""

import json

from app.models import JobPosting, Profile
from app.services.llm_client import call_structured_tool

_SYSTEM = (
    "You help a real job candidate prepare for an interview. Generate likely "
    "interview questions for this specific job, and STAR-format (Situation, Task, "
    "Action, Result) answers built ONLY from the candidate's real profile — their "
    "actual work history, projects, and achievements. Never invent a situation, "
    "action, or result that isn't grounded in the profile. If the profile doesn't "
    "have a strong example for a likely question, say so in the answer rather than "
    "inventing one — an honest 'here's the closest real example I have' is more "
    "useful than a fabricated perfect story."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "questions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question": {"type": "string"},
                    "category": {
                        "type": "string",
                        "enum": ["behavioral", "technical", "situational", "company_role_fit"],
                    },
                    "why_likely": {
                        "type": "string",
                        "description": "One sentence on why this question fits this job posting.",
                    },
                },
                "required": ["question", "category", "why_likely"],
            },
            "description": "8-12 likely interview questions for this role.",
        },
        "story_bank": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Short label, e.g. 'Payments latency fix'."},
                    "relevant_for": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Which question(s)/themes this story answers well.",
                    },
                    "situation": {"type": "string"},
                    "task": {"type": "string"},
                    "action": {"type": "string"},
                    "result": {
                        "type": "string",
                        "description": "Real outcome/metric from the profile. Do not invent a number that isn't there.",
                    },
                    "grounded_in": {
                        "type": "string",
                        "description": "Which real profile entry (role, project, or achievement) this story is built from.",
                    },
                },
                "required": ["title", "situation", "task", "action", "result", "grounded_in"],
            },
            "description": "4-8 STAR stories built from real achievements, each reusable across multiple questions.",
        },
    },
    "required": ["questions", "story_bank"],
}


def _profile_to_context(profile: Profile) -> str:
    return json.dumps(
        {
            "summary": profile.summary,
            "work_history": profile.work_history,
            "projects": profile.projects,
            "achievements": profile.achievements,
        },
        indent=2,
    )


def generate_interview_prep(profile: Profile, job: JobPosting) -> dict:
    user_message = (
        f"CANDIDATE'S REAL PROFILE (only source of real examples):\n"
        f"{_profile_to_context(profile)}\n\n"
        f"JOB POSTING:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Requirements: {job.requirements}\n\n"
        f"Full posting text:\n{job.raw_text}\n\n"
        f"Generate the question bank and story bank now."
    )
    return call_structured_tool(
        system=_SYSTEM,
        user_message=user_message,
        tool_name="record_interview_prep",
        tool_description="Record the interview question bank and STAR story bank.",
        input_schema=_SCHEMA,
        max_tokens=4096,
    )
