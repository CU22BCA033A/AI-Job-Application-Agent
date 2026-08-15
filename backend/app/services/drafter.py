"""Drafter agent: tailors a resume and cover letter to a specific job.

Hard rule, enforced by prompt (and re-checked by a separate Reviewer pass —
see services/reviewer.py): this agent may only reorder, reword, or select
among facts that already exist in the candidate's profile. It never invents
a skill, project, employer, or metric. Every real bullet it draws from is
handed to it explicitly in the prompt so there's no ambiguity about what
"real" means here.
"""

import json

from app.models import JobPosting, Profile
from app.services.llm_client import call_structured_tool

_SYSTEM = (
    "You are a resume and cover letter writer for a real job seeker. You tailor "
    "documents to a specific job posting using ONLY the facts in the candidate's "
    "profile — you never invent a skill, employer, project, metric, or achievement "
    "that isn't already there. Your job is to reorder, reword, and select among real "
    "content to emphasize what's relevant to this posting — never to add anything. "
    "If the profile doesn't have something the job wants, leave it out; do not "
    "paper over the gap with invented experience. Keep the voice natural and human, "
    "not generic corporate filler."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "resume": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "2-3 sentence professional summary, reworded from the profile's real summary/experience to emphasize fit for this job. Must not introduce new claims.",
                },
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
                            "bullets": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Reworded/reordered versions of this role's REAL bullets from the profile, emphasizing relevance to the job. Same underlying facts, same metrics — different wording/order/emphasis only.",
                            },
                        },
                        "required": ["company", "title", "bullets"],
                    },
                    "description": "Same roles as the profile's work_history, same real bullets underneath, tailored wording/order/emphasis.",
                },
                "skills_highlighted": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Skills from the profile's real skills list, reordered to put the most job-relevant ones first. Do not add skills not in the profile.",
                },
            },
            "required": ["summary", "work_history", "skills_highlighted"],
        },
        "cover_letter": {
            "type": "object",
            "properties": {
                "greeting": {"type": "string", "description": "e.g. 'Dear Hiring Team,'"},
                "paragraphs": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "3-4 body paragraphs in the candidate's voice, drawing only on real profile facts and connecting them to this specific job.",
                },
                "closing": {"type": "string", "description": "e.g. 'Sincerely, <candidate name>'"},
            },
            "required": ["greeting", "paragraphs", "closing"],
        },
        "changes_summary": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short bullet list (3-6 items) of what was reordered/reworded/emphasized and why, for the candidate to review at a glance.",
        },
    },
    "required": ["resume", "cover_letter", "changes_summary"],
}


def _profile_to_context(profile: Profile) -> str:
    return json.dumps(
        {
            "full_name": profile.full_name,
            "summary": profile.summary,
            "work_history": profile.work_history,
            "education": profile.education,
            "skills": profile.skills,
            "projects": profile.projects,
            "achievements": profile.achievements,
        },
        indent=2,
    )


def draft_documents(profile: Profile, job: JobPosting) -> dict:
    user_message = (
        f"CANDIDATE PROFILE (the only source of real facts you may draw from):\n"
        f"{_profile_to_context(profile)}\n\n"
        f"JOB POSTING:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Requirements: {job.requirements}\n"
        f"Keywords: {job.keywords}\n\n"
        f"Full posting text:\n{job.raw_text}\n\n"
        f"Fit notes from an earlier evaluation (for context, not new facts):\n"
        f"Strengths: {job.fit_strengths}\n"
        f"Gaps: {job.fit_gaps}\n\n"
        f"Draft a tailored resume and cover letter for this candidate and this job."
    )
    return call_structured_tool(
        system=_SYSTEM,
        user_message=user_message,
        tool_name="record_draft",
        tool_description="Record the tailored resume and cover letter draft.",
        input_schema=_SCHEMA,
        max_tokens=4096,
    )
