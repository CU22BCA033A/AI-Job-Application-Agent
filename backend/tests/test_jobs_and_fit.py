FAKE_EXTRACTION = {
    "title": "Senior Backend Engineer",
    "company": "Northwind Systems",
    "location": "Remote",
    "salary_range": "$150k-$180k",
    "requirements": ["5+ years backend experience", "Kafka", "PostgreSQL"],
    "keywords": ["Python", "Kafka", "PostgreSQL", "distributed systems"],
}

FAKE_FIT_STRONG = {
    "fit_score": 88,
    "strengths": ["Direct Kafka + PostgreSQL experience", "Led a comparable latency project"],
    "gaps": ["No stated experience with their specific cloud provider"],
    "reasoning": "Strong overlap between real production experience and the posting's core requirements.",
    "recommendation": "tailor_and_apply",
}

FAKE_FIT_WEAK = {
    "fit_score": 22,
    "strengths": [],
    "gaps": ["No backend experience listed", "None of the required tools appear in the profile"],
    "reasoning": "The profile shows no overlap with this posting's core requirements.",
    "recommendation": "skip",
}


def _seed_profile(client):
    client.put(
        "/api/profile",
        json={
            "full_name": "Asha Rao",
            "email": "asha@example.com",
            "phone": "",
            "location": "",
            "links": {},
            "summary": "",
            "work_history": [
                {
                    "company": "Fintrust",
                    "title": "Senior Backend Engineer",
                    "bullets": ["Cut p99 latency 42% by redesigning the payments queue."],
                    "skills_used": ["Python", "Kafka", "PostgreSQL"],
                }
            ],
            "education": [],
            "skills": [{"name": "Python"}, {"name": "Kafka"}, {"name": "PostgreSQL"}],
            "projects": [],
            "achievements": [],
        },
    )


def test_create_job_extracts_fields(client, monkeypatch):
    monkeypatch.setattr("app.routers.jobs.extract_job_fields", lambda raw_text: FAKE_EXTRACTION)

    r = client.post("/api/jobs", json={"raw_text": "We are hiring a Senior Backend Engineer..."})
    assert r.status_code == 200
    job = r.json()
    assert job["title"] == "Senior Backend Engineer"
    assert job["company"] == "Northwind Systems"
    assert job["status"] == "new"
    assert job["fit_score"] is None


def test_full_fit_evaluation_flow_strong_match(client, monkeypatch):
    """This is the core promise of the app: paste a posting, get an honest fit score."""
    _seed_profile(client)
    monkeypatch.setattr("app.routers.jobs.extract_job_fields", lambda raw_text: FAKE_EXTRACTION)
    monkeypatch.setattr("app.routers.jobs.evaluate_fit", lambda profile, job: FAKE_FIT_STRONG)

    create = client.post("/api/jobs", json={"raw_text": "We are hiring a Senior Backend Engineer..."})
    job_id = create.json()["id"]
    assert create.json()["status"] == "new"

    evaluated = client.post(f"/api/jobs/{job_id}/evaluate")
    assert evaluated.status_code == 200
    body = evaluated.json()
    assert body["status"] == "evaluated"
    assert body["fit_score"] == 88
    assert body["fit_recommendation"] == "tailor_and_apply"
    assert "Kafka" in " ".join(body["fit_strengths"])

    # persisted, not just returned
    fetched = client.get(f"/api/jobs/{job_id}").json()
    assert fetched["fit_score"] == 88


def test_weak_fit_recommends_skip(client, monkeypatch):
    _seed_profile(client)
    monkeypatch.setattr("app.routers.jobs.extract_job_fields", lambda raw_text: FAKE_EXTRACTION)
    monkeypatch.setattr("app.routers.jobs.evaluate_fit", lambda profile, job: FAKE_FIT_WEAK)

    create = client.post("/api/jobs", json={"raw_text": "Completely unrelated posting..."})
    job_id = create.json()["id"]

    evaluated = client.post(f"/api/jobs/{job_id}/evaluate")
    body = evaluated.json()
    assert body["fit_score"] == 22
    assert body["fit_recommendation"] == "skip"


def test_kanban_status_transitions(client, monkeypatch):
    monkeypatch.setattr("app.routers.jobs.extract_job_fields", lambda raw_text: FAKE_EXTRACTION)
    job_id = client.post("/api/jobs", json={"raw_text": "..."}).json()["id"]

    r = client.patch(f"/api/jobs/{job_id}/status", json={"status": "drafting"})
    assert r.status_code == 200
    assert r.json()["status"] == "drafting"

    r = client.patch(f"/api/jobs/{job_id}/status", json={"status": "submitted"})
    assert r.json()["status"] == "submitted"


def test_job_list_and_delete(client, monkeypatch):
    monkeypatch.setattr("app.routers.jobs.extract_job_fields", lambda raw_text: FAKE_EXTRACTION)
    job_id = client.post("/api/jobs", json={"raw_text": "..."}).json()["id"]

    assert len(client.get("/api/jobs").json()) == 1

    r = client.delete(f"/api/jobs/{job_id}")
    assert r.status_code == 204
    assert client.get("/api/jobs").json() == []
    assert client.get(f"/api/jobs/{job_id}").status_code == 404
