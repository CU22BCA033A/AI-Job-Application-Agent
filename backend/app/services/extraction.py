"""Parses a pasted job posting (URL fetch is out of scope for v1 — paste text)
into structured fields: title, company, location, salary, requirements, keywords.
"""

from app.services.llm_client import call_structured_tool

_SYSTEM = (
    "You extract structured fields from a job posting's raw text. Only use "
    "information present in the text — if something isn't stated (e.g. salary), "
    "leave it blank or as an empty list rather than guessing."
)

_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string", "description": "Job title as posted."},
        "company": {"type": "string", "description": "Hiring company name."},
        "location": {
            "type": "string",
            "description": "Location or 'Remote' if stated, else empty string.",
        },
        "salary_range": {
            "type": "string",
            "description": "Salary range exactly as stated, or empty string if not mentioned.",
        },
        "requirements": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Concrete required/preferred qualifications, each as a short phrase.",
        },
        "keywords": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "Skills, tools, and terms an ATS or recruiter would scan for "
                "(e.g. 'Python', 'AWS', 'stakeholder management')."
            ),
        },
    },
    "required": ["title", "company", "location", "salary_range", "requirements", "keywords"],
}


def extract_job_fields(raw_text: str) -> dict:
    return call_structured_tool(
        system=_SYSTEM,
        user_message=f"Job posting text:\n\n{raw_text}",
        tool_name="extract_job_fields",
        tool_description="Record the structured fields extracted from this job posting.",
        input_schema=_SCHEMA,
    )
