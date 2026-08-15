# Deploying Vrutti to Vercel

Vrutti deploys as **two separate Vercel projects from this one repo** — a
static frontend and a Python serverless API — plus a small managed Postgres
database. This is the standard pattern for a Vite + FastAPI app on Vercel;
trying to force both into a single project adds complexity without any real
benefit here.

Total time: about 15 minutes, and everything below fits in Vercel's and
Neon's free tiers.

```
                 ┌─────────────────────┐
   browser  ───▶ │  vrutti-web          │  Vercel project #1
                 │  (Vite static build) │  Root Directory: frontend
                 └──────────┬───────────┘
                             │ fetch() calls, CORS
                             ▼
                 ┌─────────────────────┐
                 │  vrutti-api          │  Vercel project #2
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
  to a repo you control) — Vercel deploys from a GitHub repo you connect.
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

## 2. Deploy the backend (`vrutti-api`)

1. In Vercel: **Add New → Project**, import your GitHub repo.
2. When asked for the **Root Directory**, set it to `backend`.
3. Framework preset: Vercel should auto-detect Python (via `backend/api/index.py`
   and `backend/requirements.txt`). If it offers a framework dropdown, pick
   "Other"/"Python" — don't let it treat this as Next.js.
4. Add environment variables (Project Settings → Environment Variables):

   | Variable | Value |
   |---|---|
   | `NVIDIA_API_KEY` | your free key from build.nvidia.com |
   | `NVIDIA_MODEL` | `meta/llama-3.3-70b-instruct` (or leave unset — that's the default) |
   | `DATABASE_URL` | the `postgresql+psycopg://...` string from step 1 |
   | `CORS_ORIGINS` | leave blank for now — you'll come back and set this after step 3 |

5. Deploy. Once it's live, note the URL, e.g. `https://vrutti-api.vercel.app`.
6. Sanity check: open `https://vrutti-api.vercel.app/api/health` in a
   browser — you should see `{"status":"ok"}`. If you see a 500, check the
   function logs in the Vercel dashboard (almost always a missing/incorrect
   `DATABASE_URL`).

## 3. Deploy the frontend (`vrutti-web`)

1. **Add New → Project** again, same GitHub repo, but this time set **Root
   Directory** to `frontend`. Vercel will auto-detect Vite.
2. Add one environment variable:

   | Variable | Value |
   |---|---|
   | `VITE_API_BASE_URL` | `https://vrutti-api.vercel.app` (your backend URL from step 2) |

3. Deploy. You'll get a URL like `https://vrutti-web.vercel.app`.

## 4. Close the loop: allow the frontend to call the backend

Go back to the **vrutti-api** project → Environment Variables, and set:

| Variable | Value |
|---|---|
| `CORS_ORIGINS` | `https://vrutti-web.vercel.app` |

Redeploy the backend project (Vercel → Deployments → ⋯ → Redeploy) so the
new env var takes effect. Without this step, the browser will block API
calls with a CORS error even though the backend itself is up.

## 5. Try it

Open your `vrutti-web.vercel.app` URL:

1. Go to **Profile**, upload a resume PDF (or paste text), review the
   parsed fields, and hit **Save profile**.
2. Go to **Jobs**, paste a real job description, hit **Evaluate fit**, and
   watch the score ring animate in.

If step 2 hangs and then errors, see "Timeouts" below.

## Things that are genuinely worth knowing

**Cold starts.** A serverless Python function that hasn't been hit in a
while takes a beat (often 1-3s) to spin up before it even starts talking to
the LLM. The first request after idle time will feel slower than the rest —
this is normal serverless behavior, not a bug.

**Timeouts.** Model calls for resume parsing or fit evaluation can take
several seconds — and free-tier inference can be slower and less
predictable than a paid frontier API, especially under load. Vercel's Hobby
(free) plan currently allows Python functions up to 60s via the
`maxDuration` setting already in `backend/vercel.json` — that's enough
headroom for any single call in this app under normal conditions. If your
account's plan enforces a lower cap, or NVIDIA NIM is slow enough to hit
even 60s, either upgrade the relevant plan tier or move the backend to a
host built for longer-running Python processes (Render and Railway both
have simple free tiers and don't impose the same per-request ceiling).

**Tool-calling reliability.** Not every model in NVIDIA's free catalog
reliably honors a forced tool/function call — if you switch `NVIDIA_MODEL`
away from the default and start seeing 502s with "didn't return the
expected response," that model likely doesn't support forced tool choice
well. Check the model's page on build.nvidia.com for tool-calling support
before switching, or revert to the default.

**This isn't "set once and forget."** Every push to the branch Vercel is
tracking triggers a new deployment automatically. If you don't want that,
disconnect auto-deploy in the project's Git settings.

**Local dev still uses SQLite by default** (`backend/.env`'s
`DATABASE_URL`) — you don't need Neon or Vercel at all to run this on your
own machine. Postgres only matters once you deploy, because serverless
functions have no persistent local disk to keep a SQLite file on.

**Data ownership.** The Postgres database is yours (Neon's free tier, your
account) — nothing here is Vrutti "storing your data" on some third-party
service beyond the NVIDIA NIM calls for extraction/evaluation and the
database you provisioned yourself.
