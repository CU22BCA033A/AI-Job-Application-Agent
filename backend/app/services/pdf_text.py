"""Extracts plain text from an uploaded resume PDF, ahead of the Claude parse step.

Pure-Python (pypdf) — no system dependencies, so this works fine on serverless.
Does not do OCR: a scanned/image-only PDF will yield little or no text, and
callers should surface that as an actionable error rather than sending an
empty document to Claude.
"""

from io import BytesIO

from fastapi import HTTPException
from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_PDF_BYTES = 10 * 1024 * 1024  # 10 MB — resumes are never legitimately larger
MIN_EXTRACTED_CHARS = 40  # below this, treat it as "no real text" (likely a scan)


def extract_text_from_pdf(file_bytes: bytes) -> str:
    if len(file_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="That PDF is larger than 10 MB — is it the right file?")

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except PdfReadError as exc:
        raise HTTPException(
            status_code=400, detail="Couldn't open that file as a PDF. Is it a valid, non-password-protected PDF?"
        ) from exc

    if reader.is_encrypted:
        raise HTTPException(
            status_code=400,
            detail="That PDF is password-protected. Remove the password and try again, or paste the text instead.",
        )

    text = "\n\n".join(page.extract_text() or "" for page in reader.pages).strip()

    if len(text) < MIN_EXTRACTED_CHARS:
        raise HTTPException(
            status_code=422,
            detail=(
                "Couldn't find selectable text in that PDF — it might be a scanned image. "
                "Try exporting your resume as a text-based PDF, or paste the text directly instead."
            ),
        )

    return text
