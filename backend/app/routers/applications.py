from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db

router = APIRouter(prefix="/api", tags=["applications"])

FOLLOWUP_AFTER_DAYS = 10


def _needs_followup(application: models.Application, job_status: models.JobStatus) -> bool:
    if application.submitted_at is None:
        return False
    if job_status not in (models.JobStatus.SUBMITTED,):
        return False  # moved on to interviewing/closed — no longer waiting on a reply
    last_touch = application.last_followup_at or application.submitted_at
    return datetime.utcnow() - last_touch >= timedelta(days=FOLLOWUP_AFTER_DAYS)


def _to_out(application: models.Application, job_status: models.JobStatus) -> schemas.ApplicationOut:
    return schemas.ApplicationOut(
        id=application.id,
        job_id=application.job_id,
        submitted_at=application.submitted_at,
        last_followup_at=application.last_followup_at,
        notes=application.notes,
        created_at=application.created_at,
        updated_at=application.updated_at,
        needs_followup=_needs_followup(application, job_status),
    )


@router.get("/applications", response_model=list[schemas.ApplicationOut])
def list_applications(db: Session = Depends(get_db)):
    """Every job that's been submitted, oldest first — the ones needing a
    follow-up float to the top for you via `needs_followup`.
    """
    applications = db.query(models.Application).all()
    return [_to_out(a, a.job.status) for a in applications]


@router.get("/jobs/{job_id}/application", response_model=schemas.ApplicationOut | None)
def get_application(job_id: str, db: Session = Depends(get_db)):
    application = db.query(models.Application).filter_by(job_id=job_id).first()
    if application is None:
        return None
    return _to_out(application, application.job.status)


@router.patch("/jobs/{job_id}/application/notes", response_model=schemas.ApplicationOut)
def update_application_notes(
    job_id: str, payload: schemas.ApplicationNotesUpdate, db: Session = Depends(get_db)
):
    application = db.query(models.Application).filter_by(job_id=job_id).first()
    if application is None:
        application = models.Application(job_id=job_id)
        db.add(application)
        db.flush()
    application.notes = payload.notes
    db.commit()
    db.refresh(application)
    return _to_out(application, application.job.status)


@router.post("/jobs/{job_id}/application/followup", response_model=schemas.ApplicationOut)
def mark_followed_up(job_id: str, db: Session = Depends(get_db)):
    """Resets the follow-up clock — call this when you've actually sent a
    nudge, so the reminder doesn't nag again until another 10 days pass.
    """
    application = db.query(models.Application).filter_by(job_id=job_id).first()
    if application is None:
        application = models.Application(job_id=job_id, submitted_at=datetime.utcnow())
        db.add(application)
        db.flush()
    application.last_followup_at = datetime.utcnow()
    db.commit()
    db.refresh(application)
    return _to_out(application, application.job.status)


@router.get("/analytics", response_model=schemas.AnalyticsOut)
def get_analytics(db: Session = Depends(get_db)):
    jobs = db.query(models.JobPosting).all()
    applications = db.query(models.Application).all()

    total_jobs = len(jobs)
    interviewing = sum(1 for j in jobs if j.status == models.JobStatus.INTERVIEWING)
    closed = sum(1 for j in jobs if j.status == models.JobStatus.CLOSED)
    responded = sum(
        1 for j in jobs if j.status in (models.JobStatus.INTERVIEWING, models.JobStatus.CLOSED)
    )
    needs_followup_count = sum(1 for a in applications if _needs_followup(a, a.job.status))
    applications_sent = sum(1 for a in applications if a.submitted_at is not None)

    return schemas.AnalyticsOut(
        total_jobs=total_jobs,
        applications_sent=applications_sent,
        interviewing=interviewing,
        closed=closed,
        response_rate=round(responded / applications_sent, 3) if applications_sent else 0.0,
        interview_rate=round(interviewing / applications_sent, 3) if applications_sent else 0.0,
        needs_followup=needs_followup_count,
    )
