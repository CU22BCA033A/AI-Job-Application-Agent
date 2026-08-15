import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class JobStatus(str, enum.Enum):
    NEW = "new"
    EVALUATED = "evaluated"
    DRAFTING = "drafting"
    READY = "ready"
    SUBMITTED = "submitted"
    INTERVIEWING = "interviewing"
    CLOSED = "closed"


class FitRecommendation(str, enum.Enum):
    TAILOR_AND_APPLY = "tailor_and_apply"
    STRETCH_TAILOR_CAREFULLY = "stretch_tailor_carefully"
    SKIP = "skip"


class DocumentType(str, enum.Enum):
    RESUME = "resume"
    COVER_LETTER = "cover_letter"
    INTERVIEW_PREP = "interview_prep"


class DocumentStatus(str, enum.Enum):
    DRAFTED = "drafted"
    REVIEWED = "reviewed"
    FLAGGED = "flagged"
    APPROVED = "approved"


class Profile(Base):
    """The single source of truth for the user's real experience.

    Every generated document must trace back to content stored here —
    the Drafter is never allowed to introduce facts that don't exist
    on this record.
    """

    __tablename__ = "profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    full_name: Mapped[str] = mapped_column(String, default="")
    email: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")
    location: Mapped[str] = mapped_column(String, default="")
    links: Mapped[dict] = mapped_column(JSON, default=dict)  # {linkedin, github, portfolio, ...}
    summary: Mapped[str] = mapped_column(Text, default="")

    # Each is a JSON list of dicts — see app/schemas.py for the shape.
    work_history: Mapped[list] = mapped_column(JSON, default=list)
    education: Mapped[list] = mapped_column(JSON, default=list)
    skills: Mapped[list] = mapped_column(JSON, default=list)
    projects: Mapped[list] = mapped_column(JSON, default=list)
    achievements: Mapped[list] = mapped_column(JSON, default=list)

    raw_resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    source_url: Mapped[str | None] = mapped_column(String, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text)

    title: Mapped[str] = mapped_column(String, default="")
    company: Mapped[str] = mapped_column(String, default="")
    location: Mapped[str] = mapped_column(String, default="")
    salary_range: Mapped[str | None] = mapped_column(String, nullable=True)
    requirements: Mapped[list] = mapped_column(JSON, default=list)
    keywords: Mapped[list] = mapped_column(JSON, default=list)

    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.NEW)

    fit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fit_reasoning: Mapped[str | None] = mapped_column(Text, nullable=True)
    fit_strengths: Mapped[list] = mapped_column(JSON, default=list)
    fit_gaps: Mapped[list] = mapped_column(JSON, default=list)
    fit_recommendation: Mapped[FitRecommendation | None] = mapped_column(
        Enum(FitRecommendation), nullable=True
    )

    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    documents: Mapped[list["GeneratedDocument"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )
    application: Mapped["Application | None"] = relationship(
        back_populates="job", cascade="all, delete-orphan", uselist=False
    )


class GeneratedDocument(Base):
    """A tailored resume or cover letter, produced by Drafter -> Reviewer."""

    __tablename__ = "generated_documents"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("job_postings.id"))
    doc_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Structured content (resume: sections/bullets; cover letter: paragraphs).
    content: Mapped[dict] = mapped_column(JSON, default=dict)

    status: Mapped[DocumentStatus] = mapped_column(Enum(DocumentStatus), default=DocumentStatus.DRAFTED)

    # Reviewer agent output: any fabrication risk, missing keywords, tone notes.
    review_notes: Mapped[list] = mapped_column(JSON, default=list)
    review_passed: Mapped[bool | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    job: Mapped[JobPosting] = relationship(back_populates="documents")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    job_id: Mapped[str] = mapped_column(ForeignKey("job_postings.id"), unique=True)

    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_followup_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    notes: Mapped[str] = mapped_column(Text, default="")

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    job: Mapped[JobPosting] = relationship(back_populates="application")
