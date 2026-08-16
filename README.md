# Vrutti (वृत्ति)

*Vrutti* is Sanskrit for "profession" or "livelihood" — the word behind
"vocation." It's a personal AI job application agent: paste a job posting,
get an honest fit score, and get help drafting a tailored resume and cover
letter, prepping for the interview, and tracking the application afterward —
using only what's actually true about you.

This is a real daily-use tool, not a demo, and it's built around one hard
rule: **it drafts, you decide.** Nothing is ever submitted automatically, and
nothing is ever invented.

**LLM provider:** Vrutti runs on [NVIDIA NIM](https://build.nvidia.com/) by
default — a free-tier, OpenAI-compatible inference API — rather than a paid
frontier model. That's a deliberate cost tradeoff, not a hidden default: the
backend's `services/llm_client.py` talks to any OpenAI-compatible endpoint,
so swapping providers later is a config change (`NVIDIA_BASE_URL` /
`NVIDIA_MODEL`), not a rewrite. The real cost of this choice is quality and
reliability — a free open-weight model is less capable and less consistent
at reliably returning structured output than a frontier model — see the
accuracy note below.

## Scope & limits — read this first

- **No auto-apply.** Vrutti never submits an application on its own. Every
  generated document is a draft you review, edit, and export yourself.
- **No fabrication.** The Drafter agent only ever rephrases or reorders
  what's in your stored profile. A second Reviewer agent — a genuinely
  separate LLM call — double-checks every draft against your real profile
  before you see it. If it can't verify something, it flags it instead of
  "fixing" it.
- **No aggressive scraping.** You paste job descriptions or URLs yourself.
  There's no login-walled scraper against LinkedIn/Indeed/etc.
- **Your data stays yours.** Locally it's a SQLite file on your machine; if
  you deploy it (see `DEPLOYMENT.md`), it's a Postgres database you own. The
  only outbound calls are to your LLM provider (NVIDIA NIM by default), using
  your own key.
- **"Accuracy" is honest, not perfect.** The fit score is a blend of two
  different signals, not just an LLM's opinion: a deterministic keyword
  match (does each term the job posting actually uses show up anywhere in
  your profile — the same blunt technique a real ATS keyword scanner uses,
  weighted 65% of the score) plus the model's holistic read of the two
  (35%, catching synonyms and transferable experience a literal keyword
  match misses). The job detail page shows exactly which keywords matched
  and which didn't, so the number is traceable to the actual posting text,
  not a black box. Extracted fields and drafted content are still the
  model's judgment, not a deterministic calculation — there's no such thing
  as a "100% accurate" LLM opinion there. What *is* guaranteed: outputs are
  structurally valid (forced function-call schemas, not parsed prose), every
  generated document goes through a separate Reviewer pass before you see
  it, and nothing is ever invented outside your stored profile. Treat the
  fit score and gaps as a strong second opinion worth reading, not gospel.
  This is doubly true on the
  free open-weight model this app runs by default — it's a smaller model
  than a frontier one, so read its output a little more skeptically.
- **Current state:** Phases 1–5 are built and tested end-to-end — profile +
  resume import (text or PDF), job intake + fit evaluation, the Drafter/
  Reviewer tailored-document pipeline with a diff view and client-side PDF
  export, application tracking with follow-up reminders and analytics, and
  interview prep (question bank + STAR story bank). See "What's next" below
  for what's still just polish.

## How it works today

1. Fill in your **Profile** — or upload an existing resume **PDF** (or paste
   its text) and let the LLM parse it into structured fields for you to
   review. Nothing is saved until you explicitly hit "Save profile."
2. Paste a **job posting** on the Jobs page. Vrutti extracts the title,
   company, requirements, and keywords.
3. Hit **Evaluate fit** — the model scores the match against your real profile
   (0–100), lists genuine strengths and gaps, and recommends "tailor &
   apply," "stretch — tailor carefully," or "skip." You'll see this land as
   an animated score ring, not a blank spinner.
4. Drag jobs between pipeline columns (New → Evaluated → Drafting → Ready →
   Submitted → Interviewing → Closed), or click a card to open its detail
   page — that's where the rest of the workflow lives.
5. On a job's detail page, hit **Generate drafts**. The **Drafter** writes a
   tailored resume (reworded/reordered bullets, never invented ones) and a
   cover letter from your real profile; the **Reviewer** — a genuinely
   separate LLM call — then checks that draft and flags anything it can't
   verify (severity-tagged notes, not silent edits). Review the side-by-side
   diff against your real resume, edit either document inline if you want,
   and **Approve** each one — once both are approved, the job auto-advances
   to "Ready."
6. **Download PDF** for either document — generated client-side (real
   selectable text, not a screenshot), so nothing leaves your browser to
   produce the file.
7. Move a job to **Submitted** and Vrutti starts tracking it: submission
   date, freeform notes, and a "worth a follow-up" flag once 10+ days pass
   without you marking a touchpoint. The **Applications** page rolls all of
   this up into response-rate/interview-rate analytics.
8. Hit **Generate prep** on a job's detail page for a likely-question bank
   and STAR-format story bank — each story explicitly grounded in a real
   achievement from your profile, not a generic template answer.

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
      documents.py             Draft/review generation, versioning, approval-gating, interview prep
      applications.py           Application tracking, follow-up reminders, analytics
    services/
      llm_client.py           Shared OpenAI-compatible tool-call wrapper (NVIDIA NIM)
      extraction.py            Job posting -> structured fields
      fit_evaluator.py          Profile + job -> fit score/gaps/recommendation
      resume_parser.py          Resume text -> structured profile
      pdf_text.py                PDF -> plain text (pypdf, no system deps)
      drafter.py                  Profile + job -> tailored resume + cover letter (never invents facts)
      reviewer.py                   Separate LLM pass that fact-checks the draft, flags rather than rewrites
      interview_prep.py               Profile + job -> question bank + STAR story bank
  tests/               Pytest suite (mocks LLM calls, proves the flow)
  requirements.txt      Runtime deps only (what gets deployed)
  requirements-dev.txt   + uvicorn/pytest/httpx for local dev
  vercel.json             maxDuration config for the API function

frontend/            Vite + React + TypeScript + Tailwind
  src/
    components/        Hero3D, FitScoreRing, EvaluationProgress, JobCard, Layout,
                          ResumeDiff, ReviewNoteList
    pages/               Landing, JobsPage, JobDetailPage, ApplicationsPage, ProfilePage
    lib/
      api.ts                Typed fetch client for the backend
      pdf.ts                  Client-side PDF export (jsPDF) for tailored documents
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
cp .env.example .env   # then add your NVIDIA_API_KEY
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
| `backend/.env` | `NVIDIA_API_KEY` | Free key from build.nvidia.com — required for extraction/fit evaluation |
| `backend/.env` | `NVIDIA_MODEL` | Defaults to `meta/llama-3.3-70b-instruct`; must support forced tool/function calling — check the model's page on build.nvidia.com before switching |
| `backend/.env` | `NVIDIA_BASE_URL` | Defaults to NVIDIA NIM's endpoint; change only to point at a different OpenAI-compatible provider |
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

- **Drafter/Reviewer are separate agent calls, not one merged prompt.** The
  Reviewer's system prompt explicitly tells it "you did NOT write these
  documents" — it only ever fact-checks against the stored profile and
  flags with a severity level (`error`/`warning`/`info`). It never silently
  rewrites a draft; a failed review shows up as a flagged document with
  notes, and approval is a human action.
- **Approval gates the pipeline, not the model.** A job only auto-advances
  to "Ready" once the latest resume *and* cover letter documents are both
  explicitly approved by you — the Reviewer passing its own check isn't
  enough on its own.
- **PDF export is client-side, deliberately.** WeasyPrint (the original
  plan) needs native Cairo/Pango libraries that don't reliably exist in a
  serverless function. Generating the PDF in the browser with jsPDF instead
  sidesteps that, and produces real selectable text (ATS-parseable), not a
  rasterized screenshot.
- **Follow-up reminders are a pure date check**, not another LLM call:
  10+ days since submission (or the last marked follow-up) while a job is
  still in "Submitted" status. No model opinion involved in when to nudge
  you.
- **Fit evaluation is read-only.** Scoring a job never drafts anything —
  the point is to let you archive low-fit postings before spending any
  tailoring effort on them.
- **Everything the model returns is structured**, via a forced function call
  (`tool_choice`), not parsed from prose — this is what makes fit scores,
  extracted fields, and (later) generated documents reliably typed. It also
  means tool-calling reliability is now a real constraint: not every model in
  NVIDIA's free catalog honors a forced tool choice consistently, which is
  why `NVIDIA_MODEL` is easy to override and a missing tool call surfaces as
  a clear 502 instead of a silent bad response (see `llm_client.py`).

## What's next (Phase 6 — polish)

Phases 1–5 are done. What's left is genuinely polish, not missing
functionality:

- A dedicated structured editor for work history/education/skills/projects
  on the Profile page (today, the fastest path is resume import + the
  Basics form; the full arrays are already there via the API).
- Optional mock-interview chat mode on top of the existing question/story
  bank.
- Code-splitting the frontend bundle (the Three.js hero pushes the main
  chunk past Vite's 500kB warning threshold — cosmetic build-log noise, not
  a functional issue).
