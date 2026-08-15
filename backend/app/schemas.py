from datetime import datetime

from pydantic import BaseModel, Field

from app.models import DocumentStatus, DocumentType, FitRecommendation, JobStatus


# ---------- Profile ----------


class WorkHistoryItem(BaseModel):
    company: str
    title: str
    location: str = ""
    start_date: str = ""  # free-form ("Jun 2021"); keep parsing forgiving
    end_date: str = ""  # "" or "Present" if current
    current: bool = False
    bullets: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)


class EducationItem(BaseModel):
    institution: str
    degree: str = ""
    field: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    notes: str = ""


class SkillItem(BaseModel):
    name: str
    category: str = ""  # e.g. "language", "framework", "tool", "soft skill"
    proficiency: str = ""  # e.g. "expert", "familiar"


class ProjectItem(BaseModel):
    name: str
    description: str = ""
    bullets: list[str] = Field(default_factory=list)
    technologies: list[str] = Field(default_factory=list)
    url: str = ""


class AchievementItem(BaseModel):
    title: str
    description: str = ""
    metric: str = ""  # the real, quantified proof (e.g. "cut latency 40%")
    date: str = ""


class ProfileBase(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    links: dict[str, str] = Field(default_factory=dict)
    summary: str = ""
    work_history: list[WorkHistoryItem] = Field(default_factory=list)
    education: list[EducationItem] = Field(default_factory=list)
    skills: list[SkillItem] = Field(default_factory=list)
    projects: list[ProjectItem] = Field(default_factory=list)
    achievements: list[AchievementItem] = Field(default_factory=list)


class ProfileCreate(ProfileBase):
    pass


class ProfileUpdate(ProfileBase):
    pass


class ProfileOut(ProfileBase):
    id: str
    raw_resume_text: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ResumeImportRequest(BaseModel):
    resume_text: str


class ResumeImportResponse(BaseModel):
    profile: ProfileBase
    notes: list[str] = Field(default_factory=list)  # anything the LLM flagged as ambiguous/needs review


# ---------- Job postings ----------


class JobCreateFromText(BaseModel):
    raw_text: str
    source_url: str | None = None


class JobOut(BaseModel):
    id: str
    source_url: str | None
    raw_text: str
    title: str
    company: str
    location: str
    salary_range: str | None
    requirements: list[str]
    keywords: list[str]
    status: JobStatus
    fit_score: int | None
    fit_reasoning: str | None
    fit_strengths: list[str]
    fit_gaps: list[str]
    fit_recommendation: FitRecommendation | None
    notes: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobStatusUpdate(BaseModel):
    status: JobStatus


class JobNotesUpdate(BaseModel):
    notes: str


class FitEvaluation(BaseModel):
    fit_score: int = Field(ge=0, le=100)
    strengths: list[str]
    gaps: list[str]
    reasoning: str
    recommendation: FitRecommendation


# ---------- Documents (drafting pipeline) ----------


class DocumentOut(BaseModel):
    id: str
    job_id: str
    doc_type: DocumentType
    version: int
    content: dict
    status: DocumentStatus
    review_notes: list[dict]
    review_passed: bool | None
    created_at: datetime

    model_config = {"from_attributes": True}


class DocumentUpdate(BaseModel):
    content: dict | None = None
    status: DocumentStatus | None = None


# ---------- Application tracking ----------


class ApplicationOut(BaseModel):
    id: str
    job_id: str
    submitted_at: datetime | None
    last_followup_at: datetime | None
    notes: str
    created_at: datetime
    updated_at: datetime
    needs_followup: bool = False  # computed: submitted, no response, >=10 days since last touch

    model_config = {"from_attributes": True}


class ApplicationNotesUpdate(BaseModel):
    notes: str


class AnalyticsOut(BaseModel):
    total_jobs: int
    applications_sent: int
    interviewing: int
    closed: int
    response_rate: float  # (interviewing + closed reached via response) / applications_sent
    interview_rate: float  # interviewing / applications_sent
    needs_followup: int


# ---------- Interview prep ----------


class InterviewQuestion(BaseModel):
    question: str
    category: str
    why_likely: str


class StoryBankEntry(BaseModel):
    title: str
    relevant_for: list[str] = Field(default_factory=list)
    situation: str
    task: str
    action: str
    result: str
    grounded_in: str


class InterviewPrepOut(BaseModel):
    id: str
    job_id: str
    questions: list[InterviewQuestion]
    story_bank: list[StoryBankEntry]
    created_at: datetime
