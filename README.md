# Vrutti (वृत्ति)

*Vrutti* is Sanskrit for "profession" or "livelihood" — the word behind
"vocation." It's a personal AI job application agent: paste a job posting,
get an honest fit score, and (as the project grows) get help drafting a
tailored resume and cover letter — using only what's actually true about you.

This is a real daily-use tool, not a demo, and it's built around one hard
rule: **it drafts, you decide.** Nothing is ever submitted automatically, and
nothing is ever invented.

## Scope & limits — read this first

- **No auto-apply.** Vrutti never submits an application on its own. Every
  generated document is a draft you review, edit, and export yourself.
- **No fabrication.** The Drafter agent (coming in a later phase) will only
  ever rephrase or reorder what's in your stored profile. A second Reviewer
  agent double-checks every draft against your real profile before you see
  it. If it can't verify something, it flags it instead of "fixing" it.
- **No aggressive scraping.** You paste job descriptions or URLs yourself.
  There's no login-walled scraper against LinkedIn/Indeed/etc.
- **Your data stays local.** Everything lives in a local SQLite database.
  The only outbound calls are to the Anthropic API, using your own key.
- **Current state:** Phases 1–2 (profile, resume import, job intake, fit
  evaluation) are fully built and tested end-to-end. The frontend shell,
  including the 3D hero and the fit-evaluation "wow moment," is live. The
  Drafter/Reviewer pipeline, PDF export, application tracking, and interview
  prep (Phases 3–5) are not built yet — see "What's next" below.

## How it works today

1. Fill in your **Profile** (or paste an existing resume and let Claude
   parse it into structured fields for you to review — nothing is saved
   until you explicitly hit save).
2. Paste a **job posting** on the Jobs page. Vrutti extracts the title,
   company, requirements, and keywords.
3. Hit **Evaluate fit** — Claude scores the match against your real profile
   (0–100), lists genuine strengths and gaps, and recommends "tailor &
   apply," "stretch — tailor carefully," or "skip." You'll see this land as
   an animated score ring, not a blank spinner.
4. Drag jobs between pipeline columns (New → Evaluated → Drafting → Ready →
   Submitted → Interviewing → Closed) as you work them.

## Project structure

```
backend/            FastAPI app
  app/
    main.py          App entrypoint, CORS, startup
    config.py         Env-based settings
    database.py        SQLAlchemy engine/session
    models.py           Profile, JobPosting, GeneratedDocument, Application
    schemas.py            Pydantic request/response shapes
    routers/
      profile.py           GET/PUT profile, resume import
      jobs.py                Job CRUD, fit evaluation, status/notes
    services/
      claude_client.py       Shared Anthropic tool-call wrapper
      extraction.py            Job posting -> structured fields
      fit_evaluator.py          Profile + job -> fit score/gaps/recommendation
      resume_parser.py          Resume text -> structured profile
  tests/               Pytest suite (mocks Claude calls, proves the flow)

frontend/            Vite + React + TypeScript + Tailwind
  src/
    components/        Hero3D, FitScoreRing, EvaluationProgress, JobCard, Layout
    pages/               Landing, JobsPage, ProfilePage
    lib/api.ts             Typed fetch client for the backend
```

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then add your ANTHROPIC_API_KEY
uvicorn app.main:app --reload --port 8000
```

Run the tests (fully mocked — no API key or network needed):

```bash
pytest
```

### Frontend

```bash
cd frontend
npm install
cp .env.example .env   # adjust VITE_API_BASE_URL if your backend isn't on :8000
npm run dev
```

Open http://localhost:5173.

### Environment variables

| File | Variable | Purpose |
|---|---|---|
| `backend/.env` | `ANTHROPIC_API_KEY` | Your key from console.anthropic.com — required for extraction/fit evaluation |
| `backend/.env` | `CLAUDE_MODEL` | Defaults to `claude-sonnet-5`; override to try another model |
| `backend/.env` | `DATABASE_URL` | Defaults to a local SQLite file; swap for Postgres when ready |
| `backend/.env` | `CORS_ORIGINS` | Comma-separated origins allowed to call the API |
| `frontend/.env` | `VITE_API_BASE_URL` | Where the frontend looks for the backend |

Never commit `.env` files — they're already in `.gitignore`.

## Design notes

- **Drafter/Reviewer are separate agent calls, not one merged prompt.** This
  keeps the anti-fabrication check real and auditable rather than a single
  model quietly "cleaning up" its own output. This structure isn't wired up
  yet (Phase 3), but `services/claude_client.py`'s `call_structured_tool`
  helper is written to support each agent as its own tool-call schema.
- **Fit evaluation is read-only.** Scoring a job never drafts anything —
  the point is to let you archive low-fit postings before spending any
  tailoring effort on them.
- **Everything Claude returns is structured**, via forced tool use
  (`tool_choice`), not parsed from prose — this is what makes fit scores,
  extracted fields, and (later) generated documents reliably typed.

## What's next (Phases 3–6)

- Drafter agent: tailored resume bullets + cover letter, generated only from
  profile content.
- Reviewer agent: fabrication/keyword/tone check, run as a genuinely separate
  pass.
- Side-by-side diff view between base and tailored resume.
- PDF export (HTML-to-PDF via WeasyPrint) for resume + cover letter.
- Application tracker: submission dates, follow-up reminders, response/
  interview rate analytics.
- Interview prep: question bank + STAR-format story bank from real
  achievements, optional mock-interview chat mode.
- A dedicated structured editor for work history/education/skills/projects
  on the Profile page (today, the fastest path is resume import + the
  Basics form; the full arrays are already there via the API).
