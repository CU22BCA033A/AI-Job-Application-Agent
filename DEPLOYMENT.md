# Deploying Vrutti

The frontend deploys to **Vercel** (a static Vite build). The backend
deploys to **Render** (a persistent Python web service) — not Vercel.
Vercel's serverless functions are built for quick request/response cycles
and enforce a real platform-level timeout that's shorter than it looks even
when `vercel.json` says otherwise, especially on the free Hobby plan; LLM
calls with forced structured output on a free-tier model regularly take
15-40+ seconds, which collides with that ceiling. Render runs the exact same
FastAPI app as a normal always-on process instead of a cold-started
function, so a slow model call is just a slow request, not a killed one.

Total time: about 20 minutes, and everything below fits in Vercel's, Render's,
and Neon's free tiers.

```
                 ┌─────────────────────┐
   browser  ───▶ │  vrutti-web          │  Vercel — static Vite build
                 │  (Vite static build) │  Root Directory: frontend
                 └──────────┬───────────┘
                             │ fetch() calls, CORS
                             ▼
                 ┌─────────────────────┐
                 │  vrutti-api          │  Render — persistent web service
                 │  (FastAPI, Python)   │  Root Directory: backend
                 └──────────┬───────────┘
                             │ DATABASE_URL
                             ▼
                 ┌─────────────────────┐
                 │  Neon Postgres       │  free serverless Postgres
                 └─────────────────────┘
```

## 0. Before you start

- Push this repo to your own GitHub account (fork it, or push this branch
  to a repo you control) — both Vercel and Render deploy from a GitHub repo
  you connect.
- Have a free NVIDIA API key ready — sign up at
  [build.nvidia.com](https://build.nvidia.com/), no card required, and
  generate a key from your account page.

## 1. Create the database (Neon)

1. Go to https://neon.tech and sign up (free tier is plenty for personal use).
2. Create a project — any name, any region (pick one close to where you'll
   set your Vercel functions' region for lower latency).
3. On the project dashboard, copy the **pooled** connection string (Neon
   shows both a direct and a "pooled connection" string — take the pooled
   one; it's built for exactly this serverless use case). It looks like:
   ```
   postgresql://user:password@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```
4. Rewrite the scheme from `postgresql://` to `postgresql+psycopg://` so
   SQLAlchemy uses the psycopg driver already in `requirements.txt`:
   ```
   postgresql+psycopg://user:password@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require
   ```
   Save this — it's your `DATABASE_URL`.

You don't need to run any migrations by hand — the backend calls
`Base.metadata.create_all()` on startup, which creates any missing tables
the first time it connects.

## 2. Deploy the backend (`vrutti-api`) — on Render

1. Go to https://render.com and sign up (GitHub login is easiest — it can
   see your repos immediately).
2. **New → Web Service**, connect your GitHub repo.
3. Configure it:

   | Field | Value |
   |---|---|
   | Root Directory | `backend` |
   | Runtime | Python 3 |
   | Build Command | `pip install -r requirements.txt` |
   | Start Command | `uvicorn app.main:app --host 0.0.0.0 --port $PORT` |
   | Instance Type | Free |

4. Add environment variables (in the same setup form, or Environment tab
   after creating the service):

   | Variable | Value |
   |---|---|
   | `NVIDIA_API_KEY` | your free key from build.nvidia.com |
   | `NVIDIA_MODEL` | `meta/llama-3.1-8b-instruct` (a small/fast model — see the note below on why size matters even off Vercel) |
   | `DATABASE_URL` | the `postgresql+psycopg://...` string from step 1 |
   | `CORS_ORIGINS` | leave blank for now — you'll come back and set this after step 3 |

5. Create the service. First deploy takes a couple of minutes.
6. Once it's live, note the URL, e.g. `https://vrutti-api.onrender.com`.
7. Sanity check: open `https://vrutti-api.onrender.com/api/health` in a
   browser — you should see `{"status":"ok"}`. If you get a 500 or the
   service fails to start, check the **Logs** tab in the Render dashboard —
   the most common cause is a missing/incorrect `DATABASE_URL`.

`backend/.python-version` pins the Python version to 3.11 so Render picks a
build with ready-made wheels for this repo's dependencies. If a build still
fails trying to compile `pydantic-core` from source (a wall of Rust/maturin
output, usually ending in a PyPI network error), Render didn't pick up that
file — add `PYTHON_VERSION` = `3.11.9` as an environment variable on the
service directly and redeploy.

(`backend/vercel.json` and `backend/api/index.py` are Vercel-specific leftovers
from an earlier deploy attempt — harmless to leave in the repo, safe to
delete once you've confirmed Render is working. They aren't used by Render.)

## 3. Deploy the frontend (`vrutti-web`) — on Vercel

1. In Vercel: **Add New → Project**, import your GitHub repo, and set **Root
   Directory** to `frontend`. Vercel will auto-detect Vite.
2. Add one environment variable:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://vrutti-api.onrender.com` (your backend URL from step 2, **no trailing slash**) |

3. Deploy. You'll get a URL like `https://vrutti-web.vercel.app`.

   Vite bakes `VITE_API_BASE_URL` into the JS bundle at **build time**, not
   read at runtime — if you ever change this variable later, you must
   trigger a new deploy (Vercel → Deployments → ⋯ → Redeploy) for it to take
   effect. A build from before the change will keep calling the old URL no
   matter what the Environment Variables page currently shows.

## 4. Close the loop: allow the frontend to call the backend

Go back to the Render **vrutti-api** service → Environment, and set:

| Variable | Value |
|---|---|
| `CORS_ORIGINS` | `https://vrutti-web.vercel.app` |

Save — Render redeploys automatically on an environment variable change.
Without this step, the browser will block API calls with a CORS error even
though the backend itself is up.

## 5. Try it

Open your `vrutti-web.vercel.app` URL:

1. Go to **Profile**, upload a resume PDF (or paste text), review the
   parsed fields, and hit **Save profile**.
2. Go to **Jobs**, paste a real job description, hit **Evaluate fit**, and
   watch the score ring animate in.

If step 2 hangs and then errors, see "Timeouts" below.

## Things that are genuinely worth knowing

**Cold starts.** Render's free tier spins a service down after about 15
minutes of no traffic, and spinning back up on the next request can take
30-60s. This is a real wait, but it's a one-time cost per idle period — once
warm, requests are fast — and unlike Vercel's serverless timeout, it's not
going to abort a slow-but-legitimate LLM call partway through.

**Timeouts.** Model calls for resume parsing, fit evaluation, or drafting
can take anywhere from a couple of seconds to 30+ seconds — free-tier
inference is slower and less predictable than a paid frontier API,
especially under load, and forced structured/function-call output is a
heavier code path than a plain chat reply. `NVIDIA_MODEL` defaults to a
small, fast model for this reason; a bigger one will be more capable but
slower and more likely to feel sluggish. The backend's own client-side
timeout (`llm_client.py`) is 55s — generous, since Render doesn't impose a
Vercel-style hard per-request ceiling, but still bounded so a genuinely
stuck request fails with a readable error instead of hanging forever.

**Tool-calling reliability.** Not every model in NVIDIA's free catalog
reliably honors a forced tool/function call — if you switch `NVIDIA_MODEL`
away from the default and start seeing 502s with "didn't return the
expected response," that model likely doesn't support forced tool choice
well. Check the model's page on build.nvidia.com for tool-calling support
before switching, or revert to the default.

**This isn't "set once and forget."** Every push to the branch each service
is tracking triggers a new deployment automatically, on both Vercel and
Render. If you don't want that, disconnect auto-deploy in each project's
settings.

**Local dev still uses SQLite by default** (`backend/.env`'s
`DATABASE_URL`) — you don't need Neon or Vercel at all to run this on your
own machine. Postgres only matters once you deploy, because serverless
functions have no persistent local disk to keep a SQLite file on.

**Data ownership.** The Postgres database is yours (Neon's free tier, your
account) — nothing here is Vrutti "storing your data" on some third-party
service beyond the NVIDIA NIM calls for extraction/evaluation and the
database you provisioned yourself.
