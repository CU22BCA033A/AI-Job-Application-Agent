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
- **Your data stays yours.** Locally it's a SQLite file on your machine; if
  you deploy it (see `DEPLOYMENT.md`), it's a Postgres database you own. The
  only outbound calls are to the Anthropic API, using your own key.
- **"Accuracy" is honest, not perfect.** The fit score, extracted fields, and
  (later) drafted content are Claude's judgment, not a deterministic
  calculation — there's no such thing as a "100% accurate" LLM opinion. What
  *is* guaranteed: outputs are structurally valid (forced tool-call schemas,
  not parsed prose), every generated document will eventually go through a
  separate Reviewer pass before you see it, and nothing is ever invented
  outside your stored profile. Treat the fit score and gaps as a strong
  second opinion worth reading, not gospel.
- **Current state:** Phases 1–2 (profile, resume import from pasted text or
  a PDF upload, job intake, fit evaluation) are fully built and tested
  end-to-end. The frontend shell, including the 3D hero and the
  fit-evaluation "wow moment," is live. The Drafter/Reviewer pipeline, PDF
  *export*, application tracking, and interview prep (Phases 3–5) are not
  built yet — see "What's next" below.

## How it works today

1. Fill in your **Profile** — or upload an existing resume **PDF** (or paste
   its text) and let Claude parse it into structured fields for you to
   review. Nothing is saved until you explicitly hit "Save profile."
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
  api/
    index.py           Vercel serverless entrypoint (re-exports app.main:app)
  app/
    main.py          App entrypoint, CORS, startup
    config.py         Env-based settings
    database.py        SQLAlchemy engine/session (serverless-safe pooling)
    models.py           Profile, JobPosting, GeneratedDocument, Application
    schemas.py            Pydantic request/response shapes
    routers/
      profile.py           GET/PUT profile, resume import (text + PDF)
      jobs.py                Job CRUD, fit evaluation, status/notes
    services/
      claude_client.py       Shared Anthropic tool-call wrapper
      extraction.py            Job posting -> structured fields
      fit_evaluator.py          Profile + job -> fit score/gaps/recommendation
      resume_parser.py          Resume text -> structured profile
      pdf_text.py                PDF -> plain text (pypdf, no system deps)
  tests/               Pytest suite (mocks Claude calls, proves the flow)
  requirements.txt      Runtime deps only (what gets deployed)
  requirements-dev.txt   + uvicorn/pytest/httpx for local dev
  vercel.json             maxDuration config for the API function

frontend/            Vite + React + TypeScript + Tailwind
  src/
    components/        Hero3D, FitScoreRing, EvaluationProgress, JobCard, Layout
    pages/               Landing, JobsPage, ProfilePage
    lib/api.ts             Typed fetch client for the backend
  vercel.json             SPA rewrite so client-side routes survive a refresh

DEPLOYMENT.md         Step-by-step Vercel + Neon Postgres deployment guide
```

## Setup

### Backend

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # runtime deps + uvicorn/pytest for local dev
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

## Deploying

See **[DEPLOYMENT.md](./DEPLOYMENT.md)** for the full walkthrough: a free
Neon Postgres database plus two Vercel projects (frontend + backend API),
env vars, and what to expect from cold starts on a serverless Python
function. Takes about 15 minutes the first time.

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
- PDF *export* for the tailored resume + cover letter (PDF *import* is
  already done). WeasyPrint was the original plan, but it needs native
  Cairo/Pango libraries that don't reliably exist in a serverless
  environment — likely candidates now are a client-side PDF library or a
  headless-browser render step, decided when this phase is actually built.
- Application tracker: submission dates, follow-up reminders, response/
  interview rate analytics.
- Interview prep: question bank + STAR-format story bank from real
  achievements, optional mock-interview chat mode.
- A dedicated structured editor for work history/education/skills/projects
  on the Profile page (today, the fastest path is resume import + the
  Basics form; the full arrays are already there via the API).
