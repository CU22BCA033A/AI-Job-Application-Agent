from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.routers.profile import _get_or_create_profile
from app.services.extraction import extract_job_fields
from app.services.fit_evaluator import evaluate_fit

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("", response_model=schemas.JobOut)
def create_job(payload: schemas.JobCreateFromText, db: Session = Depends(get_db)):
    """Adds a job posting from pasted text (or text + the URL it came from) and
    immediately extracts structured fields, so it's readable in the list right away.
    Fit evaluation is a separate step — see POST /api/jobs/{id}/evaluate.
    """
    extracted = extract_job_fields(payload.raw_text)
    job = models.JobPosting(
        source_url=payload.source_url,
        raw_text=payload.raw_text,
        title=extracted.get("title", ""),
        company=extracted.get("company", ""),
        location=extracted.get("location", ""),
        salary_range=extracted.get("salary_range") or None,
        requirements=extracted.get("requirements", []),
        keywords=extracted.get("keywords", []),
        status=models.JobStatus.NEW,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[schemas.JobOut])
def list_jobs(db: Session = Depends(get_db)):
    return db.query(models.JobPosting).order_by(models.JobPosting.created_at.desc()).all()


def _get_job_or_404(job_id: str, db: Session) -> models.JobPosting:
    job = db.get(models.JobPosting, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job posting not found.")
    return job


@router.get("/{job_id}", response_model=schemas.JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    return _get_job_or_404(job_id, db)


@router.post("/{job_id}/evaluate", response_model=schemas.JobOut)
def evaluate_job(job_id: str, db: Session = Depends(get_db)):
    """Runs the Fit Evaluator against the current profile and stores the result."""
    job = _get_job_or_404(job_id, db)
    profile = _get_or_create_profile(db)

    result = evaluate_fit(profile, job)

    job.fit_score = result["fit_score"]
    job.fit_strengths = result["strengths"]
    job.fit_gaps = result["gaps"]
    job.fit_reasoning = result["reasoning"]
    job.fit_recommendation = models.FitRecommendation(result["recommendation"])
    job.fit_keyword_analysis = result["keyword_analysis"]
    job.status = models.JobStatus.EVALUATED
    db.commit()
    db.refresh(job)
    return job


@router.patch("/{job_id}/status", response_model=schemas.JobOut)
def update_job_status(job_id: str, payload: schemas.JobStatusUpdate, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    job.status = payload.status

    # Moving a job to Submitted starts its application record — this is the
    # only place submitted_at gets set, so the follow-up clock always starts
    # from when you actually marked it sent, not from some other action.
    if payload.status == models.JobStatus.SUBMITTED:
        application = db.query(models.Application).filter_by(job_id=job.id).first()
        if application is None:
            application = models.Application(job_id=job.id)
            db.add(application)
        if application.submitted_at is None:
            application.submitted_at = datetime.utcnow()

    db.commit()
    db.refresh(job)
    return job


@router.patch("/{job_id}/notes", response_model=schemas.JobOut)
def update_job_notes(job_id: str, payload: schemas.JobNotesUpdate, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    job.notes = payload.notes
    db.commit()
    db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
def delete_job(job_id: str, db: Session = Depends(get_db)):
    job = _get_job_or_404(job_id, db)
    db.delete(job)
    db.commit()
