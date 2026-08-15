from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.database import get_db
from app.services.pdf_text import extract_text_from_pdf
from app.services.resume_parser import parse_resume_text

router = APIRouter(prefix="/api/profile", tags=["profile"])


def _get_or_create_profile(db: Session) -> models.Profile:
    """This is a single-user tool — there's exactly one profile, created lazily."""
    profile = db.query(models.Profile).first()
    if profile is None:
        profile = models.Profile()
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


@router.get("", response_model=schemas.ProfileOut)
def get_profile(db: Session = Depends(get_db)):
    return _get_or_create_profile(db)


@router.put("", response_model=schemas.ProfileOut)
def update_profile(payload: schemas.ProfileUpdate, db: Session = Depends(get_db)):
    profile = _get_or_create_profile(db)
    data = payload.model_dump()
    for field, value in data.items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile


@router.post("/import", response_model=schemas.ResumeImportResponse)
def import_resume(payload: schemas.ResumeImportRequest):
    """Parses pasted resume text into the structured profile shape.

    Returned for the user to review and correct in the UI — this endpoint
    does NOT save anything, so a bad parse never silently overwrites real data.
    """
    parsed = parse_resume_text(payload.resume_text)
    notes = parsed.pop("parsing_notes", [])
    return schemas.ResumeImportResponse(profile=schemas.ProfileBase(**parsed), notes=notes)


@router.post("/import/pdf", response_model=schemas.ResumeImportResponse)
async def import_resume_pdf(file: UploadFile):
    """Same as /import, but starting from an uploaded PDF instead of pasted text.

    Text is extracted locally (pypdf, no external service) before being sent
    to the LLM for parsing. Like /import, nothing is saved until you review
    and hit "Save profile" in the UI.
    """
    file_bytes = await file.read()
    resume_text = extract_text_from_pdf(file_bytes)
    parsed = parse_resume_text(resume_text)
    notes = parsed.pop("parsing_notes", [])
    return schemas.ResumeImportResponse(profile=schemas.ProfileBase(**parsed), notes=notes)
