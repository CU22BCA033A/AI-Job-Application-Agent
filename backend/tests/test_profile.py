def test_get_profile_creates_default(client):
    r = client.get("/api/profile")
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == ""
    assert data["work_history"] == []


def test_update_profile_persists_real_data(client):
    payload = {
        "full_name": "Asha Rao",
        "email": "asha@example.com",
        "phone": "555-0100",
        "location": "Bengaluru, India",
        "links": {"linkedin": "linkedin.com/in/asharao"},
        "summary": "Backend engineer focused on distributed systems.",
        "work_history": [
            {
                "company": "Fintrust",
                "title": "Senior Backend Engineer",
                "location": "Bengaluru",
                "start_date": "Jun 2021",
                "end_date": "",
                "current": True,
                "bullets": ["Cut p99 latency 42% by redesigning the payments queue."],
                "skills_used": ["Python", "Kafka", "PostgreSQL"],
            }
        ],
        "education": [],
        "skills": [{"name": "Python", "category": "language", "proficiency": "expert"}],
        "projects": [],
        "achievements": [
            {"title": "Led payments re-architecture", "metric": "42% latency reduction", "date": "2023"}
        ],
    }
    r = client.put("/api/profile", json=payload)
    assert r.status_code == 200
    data = r.json()
    assert data["full_name"] == "Asha Rao"
    assert data["work_history"][0]["company"] == "Fintrust"
    assert data["achievements"][0]["metric"] == "42% latency reduction"

    # confirm it actually persisted, not just echoed back
    r2 = client.get("/api/profile")
    assert r2.json()["full_name"] == "Asha Rao"


def test_import_resume_does_not_save_profile(client, monkeypatch):
    def fake_parse(resume_text: str) -> dict:
        return {
            "full_name": "Asha Rao",
            "email": "asha@example.com",
            "phone": "",
            "location": "",
            "links": {},
            "summary": "",
            "work_history": [],
            "education": [],
            "skills": [],
            "projects": [],
            "achievements": [],
            "parsing_notes": ["Could not determine graduation year."],
        }

    monkeypatch.setattr("app.routers.profile.parse_resume_text", fake_parse)

    r = client.post("/api/profile/import", json={"resume_text": "Asha Rao\nSenior Engineer..."})
    assert r.status_code == 200
    body = r.json()
    assert body["profile"]["full_name"] == "Asha Rao"
    assert body["notes"] == ["Could not determine graduation year."]

    # importing must never silently overwrite the real stored profile
    stored = client.get("/api/profile").json()
    assert stored["full_name"] == ""
