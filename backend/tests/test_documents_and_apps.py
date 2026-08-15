from datetime import datetime, timedelta

FAKE_DRAFT = {
    "resume": {
        "summary": "Backend engineer with a track record of cutting production latency.",
        "work_history": [
            {
                "company": "Fintrust",
                "title": "Senior Backend Engineer",
                "location": "Bengaluru",
                "start_date": "Jun 2021",
                "end_date": "",
                "current": True,
                "bullets": ["Redesigned the payments queue, cutting p99 latency 42%."],
            }
        ],
        "skills_highlighted": ["Python", "Kafka", "PostgreSQL"],
    },
    "cover_letter": {
        "greeting": "Dear Hiring Team,",
        "paragraphs": ["I'm excited to apply for this role because..."],
        "closing": "Sincerely, Asha Rao",
    },
    "changes_summary": ["Reordered skills to lead with Kafka since the posting emphasizes it."],
}

FAKE_REVIEW_CLEAN = {
    "resume_passed": True,
    "resume_notes": [{"severity": "info", "message": "Looks accurate."}],
    "cover_letter_passed": True,
    "cover_letter_notes": [],
}

FAKE_REVIEW_FLAGGED = {
    "resume_passed": False,
    "resume_notes": [
        {"severity": "error", "message": "'led a team of 12' does not appear anywhere in the profile."}
    ],
    "cover_letter_passed": True,
    "cover_letter_notes": [],
}

FAKE_INTERVIEW_PREP = {
    "questions": [
        {
            "question": "Tell me about a time you improved system performance.",
            "category": "behavioral",
            "why_likely": "The posting emphasizes backend performance work.",
        }
    ],
    "story_bank": [
        {
            "title": "Payments latency fix",
            "relevant_for": ["performance", "ownership"],
            "situation": "Payments queue was causing p99 latency spikes.",
            "task": "Redesign the queue without downtime.",
            "action": "Introduced batching and backpressure.",
            "result": "Cut p99 latency 42%.",
            "grounded_in": "Fintrust — Senior Backend Engineer",
        }
    ],
}


def _create_evaluated_job(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.jobs.extract_job_fields",
        lambda raw_text: {
            "title": "Senior Backend Engineer",
            "company": "Northwind",
            "location": "Remote",
            "salary_range": "",
            "requirements": ["Kafka"],
            "keywords": ["Python", "Kafka"],
        },
    )
    job = client.post("/api/jobs", json={"raw_text": "We are hiring..."}).json()
    return job["id"]


def test_generate_documents_creates_resume_and_cover_letter(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    monkeypatch.setattr("app.routers.documents.draft_documents", lambda profile, job: FAKE_DRAFT)
    monkeypatch.setattr(
        "app.routers.documents.review_documents", lambda profile, job, draft: FAKE_REVIEW_CLEAN
    )

    r = client.post(f"/api/jobs/{job_id}/documents/generate")
    assert r.status_code == 200
    docs = r.json()
    assert len(docs) == 2
    doc_types = {d["doc_type"] for d in docs}
    assert doc_types == {"resume", "cover_letter"}
    assert all(d["status"] == "reviewed" for d in docs)
    assert all(d["review_passed"] is True for d in docs)

    job = client.get(f"/api/jobs/{job_id}").json()
    assert job["status"] == "drafting"


def test_generate_documents_flags_fabrication(client, monkeypatch):
    """The core anti-fabrication promise: a Reviewer finding must survive to
    the document's stored status and notes, not get silently swallowed.
    """
    job_id = _create_evaluated_job(client, monkeypatch)
    monkeypatch.setattr("app.routers.documents.draft_documents", lambda profile, job: FAKE_DRAFT)
    monkeypatch.setattr(
        "app.routers.documents.review_documents", lambda profile, job, draft: FAKE_REVIEW_FLAGGED
    )

    docs = client.post(f"/api/jobs/{job_id}/documents/generate").json()
    resume = next(d for d in docs if d["doc_type"] == "resume")
    assert resume["status"] == "flagged"
    assert resume["review_passed"] is False
    assert "does not appear" in resume["review_notes"][0]["message"]


def test_approving_both_documents_moves_job_to_ready(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    monkeypatch.setattr("app.routers.documents.draft_documents", lambda profile, job: FAKE_DRAFT)
    monkeypatch.setattr(
        "app.routers.documents.review_documents", lambda profile, job, draft: FAKE_REVIEW_CLEAN
    )
    docs = client.post(f"/api/jobs/{job_id}/documents/generate").json()

    resume_id = next(d["id"] for d in docs if d["doc_type"] == "resume")
    cover_id = next(d["id"] for d in docs if d["doc_type"] == "cover_letter")

    r1 = client.patch(f"/api/jobs/documents/{resume_id}", json={"status": "approved"})
    assert r1.status_code == 200
    # Only one of two approved — job shouldn't jump to Ready yet.
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "drafting"

    r2 = client.patch(f"/api/jobs/documents/{cover_id}", json={"status": "approved"})
    assert r2.status_code == 200
    assert client.get(f"/api/jobs/{job_id}").json()["status"] == "ready"


def test_editing_document_content_persists(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    monkeypatch.setattr("app.routers.documents.draft_documents", lambda profile, job: FAKE_DRAFT)
    monkeypatch.setattr(
        "app.routers.documents.review_documents", lambda profile, job, draft: FAKE_REVIEW_CLEAN
    )
    docs = client.post(f"/api/jobs/{job_id}/documents/generate").json()
    resume_id = next(d["id"] for d in docs if d["doc_type"] == "resume")

    edited = {**FAKE_DRAFT["resume"], "summary": "Edited by the human."}
    r = client.patch(f"/api/jobs/documents/{resume_id}", json={"content": edited})
    assert r.json()["content"]["summary"] == "Edited by the human."


def test_document_regeneration_increments_version(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    monkeypatch.setattr("app.routers.documents.draft_documents", lambda profile, job: FAKE_DRAFT)
    monkeypatch.setattr(
        "app.routers.documents.review_documents", lambda profile, job, draft: FAKE_REVIEW_CLEAN
    )
    client.post(f"/api/jobs/{job_id}/documents/generate")
    docs_v2 = client.post(f"/api/jobs/{job_id}/documents/generate").json()
    resume_v2 = next(d for d in docs_v2 if d["doc_type"] == "resume")
    assert resume_v2["version"] == 2


def test_interview_prep_generate_and_fetch(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    monkeypatch.setattr(
        "app.routers.documents.generate_interview_prep", lambda profile, job: FAKE_INTERVIEW_PREP
    )

    r = client.post(f"/api/jobs/{job_id}/interview-prep")
    assert r.status_code == 200
    body = r.json()
    assert body["questions"][0]["question"].startswith("Tell me about")
    assert body["story_bank"][0]["grounded_in"] == "Fintrust — Senior Backend Engineer"

    fetched = client.get(f"/api/jobs/{job_id}/interview-prep").json()
    assert fetched["job_id"] == job_id
    assert len(fetched["story_bank"]) == 1


def test_interview_prep_returns_null_before_generation(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    r = client.get(f"/api/jobs/{job_id}/interview-prep")
    assert r.status_code == 200
    assert r.json() is None


# ---------- Application tracking ----------


def test_marking_submitted_creates_application(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)

    r = client.patch(f"/api/jobs/{job_id}/status", json={"status": "submitted"})
    assert r.status_code == 200

    app_data = client.get(f"/api/jobs/{job_id}/application").json()
    assert app_data is not None
    assert app_data["submitted_at"] is not None
    assert app_data["needs_followup"] is False  # just submitted, no 10-day wait yet


def test_marking_submitted_twice_does_not_reset_submitted_at(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    client.patch(f"/api/jobs/{job_id}/status", json={"status": "submitted"})
    first = client.get(f"/api/jobs/{job_id}/application").json()

    client.patch(f"/api/jobs/{job_id}/status", json={"status": "interviewing"})
    client.patch(f"/api/jobs/{job_id}/status", json={"status": "submitted"})
    second = client.get(f"/api/jobs/{job_id}/application").json()

    assert first["submitted_at"] == second["submitted_at"]


def test_application_notes_and_followup(client, monkeypatch):
    job_id = _create_evaluated_job(client, monkeypatch)
    client.patch(f"/api/jobs/{job_id}/status", json={"status": "submitted"})

    r = client.patch(f"/api/jobs/{job_id}/application/notes", json={"notes": "Recruiter said 2 weeks."})
    assert r.json()["notes"] == "Recruiter said 2 weeks."

    r = client.post(f"/api/jobs/{job_id}/application/followup")
    assert r.json()["last_followup_at"] is not None


def test_needs_followup_after_ten_days():
    """Unit-tests the pure follow-up rule directly, since the flow only
    exercises the "just submitted" case (needs_followup is deterministically
    false immediately after submission).
    """
    from app.models import Application, JobStatus
    from app.routers.applications import _needs_followup

    stale = Application(job_id="j1", submitted_at=datetime.utcnow() - timedelta(days=11))
    assert _needs_followup(stale, JobStatus.SUBMITTED) is True

    fresh = Application(job_id="j2", submitted_at=datetime.utcnow() - timedelta(days=2))
    assert _needs_followup(fresh, JobStatus.SUBMITTED) is False

    # Already moved to interviewing — not "waiting on a reply" anymore.
    moved_on = Application(job_id="j3", submitted_at=datetime.utcnow() - timedelta(days=20))
    assert _needs_followup(moved_on, JobStatus.INTERVIEWING) is False


def test_analytics_counts_and_rates(client, monkeypatch):
    job1 = _create_evaluated_job(client, monkeypatch)
    job2 = _create_evaluated_job(client, monkeypatch)
    job3 = _create_evaluated_job(client, monkeypatch)

    client.patch(f"/api/jobs/{job1}/status", json={"status": "submitted"})
    client.patch(f"/api/jobs/{job2}/status", json={"status": "submitted"})
    client.patch(f"/api/jobs/{job2}/status", json={"status": "interviewing"})
    # job3 stays at "new" — never applied

    analytics = client.get("/api/analytics").json()
    assert analytics["total_jobs"] == 3
    assert analytics["applications_sent"] == 2
    assert analytics["interviewing"] == 1
    assert analytics["response_rate"] == 0.5
    assert analytics["interview_rate"] == 0.5
