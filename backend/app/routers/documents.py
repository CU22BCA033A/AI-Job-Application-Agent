from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.jobs import _get_job_or_404
from app.routers.profile import _get_or_create_profile
from app.services.drafter import draft_documents
from app.services.interview_prep import generate_interview_prep
from app.services.reviewer import review_documents

router = APIRouter(prefix="/api/jobs", tags=["documents"])

_RESUME_COVER_TYPES = (models.DocumentType.RESUME, models.DocumentType.COVER_LETTER)


def _next_version(db: Session, job_id: str, doc_type: models.DocumentType) -> int:
    existing = (
        db.query(models.GeneratedDocument)
        .filter_by(job_id=job_id, doc_type=doc_type)
        .order_by(models.GeneratedDocument.version.desc())
        .first()
    )
    return (existing.version + 1) if existing else 1


@router.post("/{job_id}/documents/generate", response_model=list[schemas.DocumentOut])
def generate_documents(job_id: str, db: Session = Depends(get_db)):
    """Runs Drafter -> Reviewer as two separate model calls and persists both
    the tailored resume and cover letter. Nothing here is ever auto-submitted —
    this only produces drafts for you to review in the UI.
    """
    job = _get_job_or_404(job_id, db)
    profile = _get_or_create_profile(db)

    draft = draft_documents(profile, job)
    review = review_documents(profile, job, draft)

    resume_doc = models.GeneratedDocument(
        job_id=job.id,
        doc_type=models.DocumentType.RESUME,
        version=_next_version(db, job.id, models.DocumentType.RESUME),
        content=draft["resume"],
        status=(
            models.DocumentStatus.FLAGGED
            if not review["resume_passed"]
            else models.DocumentStatus.REVIEWED
        ),
        review_notes=review["resume_notes"],
        review_passed=review["resume_passed"],
    )
    cover_letter_doc = models.GeneratedDocument(
        job_id=job.id,
        doc_type=models.DocumentType.COVER_LETTER,
        version=_next_version(db, job.id, models.DocumentType.COVER_LETTER),
        content=draft["cover_letter"],
        status=(
            models.DocumentStatus.FLAGGED
            if not review["cover_letter_passed"]
            else models.DocumentStatus.REVIEWED
        ),
        review_notes=review["cover_letter_notes"],
        review_passed=review["cover_letter_passed"],
    )
    db.add(resume_doc)
    db.add(cover_letter_doc)

    job.status = models.JobStatus.DRAFTING
    db.commit()
    db.refresh(resume_doc)
    db.refresh(cover_letter_doc)
    return [resume_doc, cover_letter_doc]


@router.get("/{job_id}/documents", response_model=list[schemas.DocumentOut])
def list_documents(job_id: str, db: Session = Depends(get_db)):
    _get_job_or_404(job_id, db)
    return (
        db.query(models.GeneratedDocument)
        .filter(
            models.GeneratedDocument.job_id == job_id,
            models.GeneratedDocument.doc_type.in_(_RESUME_COVER_TYPES),
        )
        .order_by(models.GeneratedDocument.created_at.desc())
        .all()
    )


def _get_document_or_404(doc_id: str, db: Session) -> models.GeneratedDocument:
    doc = db.get(models.GeneratedDocument, doc_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc


@router.patch("/documents/{doc_id}", response_model=schemas.DocumentOut)
def update_document(doc_id: str, payload: schemas.DocumentUpdate, db: Session = Depends(get_db)):
    """Save your edits to a draft, and/or approve it. Approving both the resume
    and cover letter for a job moves it to Ready in the pipeline.
    """
    doc = _get_document_or_404(doc_id, db)
    if payload.content is not None:
        doc.content = payload.content
    if payload.status is not None:
        doc.status = payload.status
    db.commit()
    db.refresh(doc)

    if doc.status == models.DocumentStatus.APPROVED:
        siblings = (
            db.query(models.GeneratedDocument)
            .filter(
                models.GeneratedDocument.job_id == doc.job_id,
                models.GeneratedDocument.doc_type.in_(_RESUME_COVER_TYPES),
            )
            .all()
        )
        latest_by_type: dict[models.DocumentType, models.GeneratedDocument] = {}
        for sibling in siblings:
            current = latest_by_type.get(sibling.doc_type)
            if current is None or sibling.version > current.version:
                latest_by_type[sibling.doc_type] = sibling
        if len(latest_by_type) == len(_RESUME_COVER_TYPES) and all(
            d.status == models.DocumentStatus.APPROVED for d in latest_by_type.values()
        ):
            job = db.get(models.JobPosting, doc.job_id)
            if job is not None:
                job.status = models.JobStatus.READY
                db.commit()

    return doc


@router.delete("/documents/{doc_id}", status_code=204)
def delete_document(doc_id: str, db: Session = Depends(get_db)):
    doc = _get_document_or_404(doc_id, db)
    db.delete(doc)
    db.commit()


# ---------- Interview prep ----------


@router.post("/{job_id}/interview-prep", response_model=schemas.InterviewPrepOut)
def generate_job_interview_prep(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    profile = _get_or_create_profile(db)

    prep = generate_interview_prep(profile, job)

    doc = models.GeneratedDocument(
        job_id=job.id,
        doc_type=models.DocumentType.INTERVIEW_PREP,
        version=_next_version(db, job.id, models.DocumentType.INTERVIEW_PREP),
        content=prep,
        status=models.DocumentStatus.DRAFTED,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return schemas.InterviewPrepOut(
        id=doc.id,
        job_id=doc.job_id,
        questions=prep["questions"],
        story_bank=prep["story_bank"],
        created_at=doc.created_at,
    )


@router.get("/{job_id}/interview-prep", response_model=schemas.InterviewPrepOut | None)
def get_job_interview_prep(job_id: str, db: Session = Depends(get_db)):
    _get_job_or_404(job_id, db)
    doc = (
        db.query(models.GeneratedDocument)
        .filter_by(job_id=job_id, doc_type=models.DocumentType.INTERVIEW_PREP)
        .order_by(models.GeneratedDocument.version.desc())
        .first()
    )
    if doc is None:
        return None
    return schemas.InterviewPrepOut(
        id=doc.id,
        job_id=doc.job_id,
        questions=doc.content.get("questions", []),
        story_bank=doc.content.get("story_bank", []),
        created_at=doc.created_at,
    )
