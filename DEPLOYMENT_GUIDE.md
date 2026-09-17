# Deployment Guide

This guide takes you from a fresh clone to a live, shareable demo URL.
It covers three paths — pick based on how much time you have left:

- **Path A — Local demo** (5 min): for practicing your pitch, no internet needed.
- **Path B — Docker Compose on one machine** (10 min): good for a judge who wants to run it themselves.
- **Path C — Free-tier cloud hosting** (30–45 min): a real public URL — Render for the backend, Vercel for the frontend. This is what you want live during judging.

---

## 0. Prerequisites

| Tool | Version | Check with |
|---|---|---|
| Python | 3.11+ | `python3 --version` |
| Node.js | 20+ | `node --version` |
| Docker (optional, Path B) | 24+ | `docker --version` |
| Git | any recent | `git --version` |
| A GitHub account | — | for Path C |
| A Render account (free) | — | https://render.com |
| A Vercel account (free) | — | https://vercel.com |

---

## Path A — Local demo

```bash
# Terminal 1 — backend
cd backend
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
cp .env.example .env            # VITE_API_URL=http://localhost:8000
npm run dev
```

Open `http://localhost:5173`. Check `http://localhost:8000/docs` for the
interactive Swagger UI if you want to demo the API directly to judges.

**Quick sanity check without the UI at all:**
```bash
curl http://localhost:8000/api/health
curl -X POST http://localhost:8000/api/chat/start -H "Content-Type: application/json" -d '{"language":"en"}'
```

---

## Path B — Docker Compose (one command, one machine)

```bash
docker compose up --build
```

This builds both images (see `backend/Dockerfile` and `frontend/Dockerfile`)
and starts:
- backend on `http://localhost:8000`
- frontend on `http://localhost:5173`, already pointed at the backend

To stop: `docker compose down`. To rebuild after a code change:
`docker compose up --build`.

This is the easiest way for a judge to run your project locally from a
GitHub clone with **zero manual setup**, so make sure this path works —
it's a strong "well-engineered project" signal.

---

## Path C — Free-tier cloud hosting (Render + Vercel)

This gives you a real public URL to put on your slide and submit in the
hackathon form. Total cost: **$0** on free tiers.

### C.1 — Push to GitHub first

```bash
git init
git add .
git commit -m "Initial commit: SwasthyaSetu AI MVP"
git branch -M main
git remote add origin https://github.com/<your-org>/swasthyasetu-ai.git
git push -u origin main
```

### C.2 — Deploy the backend to Render

1. Go to https://dashboard.render.com → **New** → **Web Service**.
2. Connect your GitHub repo, select it.
3. Configure:
   - **Root Directory**: `backend`
   - **Runtime**: Docker (Render auto-detects `backend/Dockerfile`) — or,
     if you prefer not to use Docker: **Environment** = Python 3, **Build
     Command** = `pip install -r requirements.txt`, **Start Command** =
     `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Instance type**: Free
4. Add environment variables (Render dashboard → Environment):
   - `ALLOWED_ORIGINS` = `https://<your-frontend-domain>.vercel.app` (you'll
     get this exact URL in step C.3 — come back and update this after)
   - Leave `BHASHINI_*` and `ANTHROPIC_API_KEY` blank unless you're using them.
5. Click **Create Web Service**. Render will build and give you a URL like
   `https://swasthyasetu-backend.onrender.com`.
6. Verify: `curl https://swasthyasetu-backend.onrender.com/api/health`

> **Free-tier note:** Render's free web services spin down after 15
> minutes of inactivity and take ~30–60 seconds to wake up on the next
> request. Hit the health endpoint a minute before you go on stage to
> "warm it up," or upgrade to a paid instance for judging day if budget allows.

### C.3 — Deploy the frontend to Vercel

1. Go to https://vercel.com/new, import the same GitHub repo.
2. Configure:
   - **Root Directory**: `frontend`
   - **Framework Preset**: Vite (auto-detected)
   - **Build Command**: `npm run build` (default)
   - **Output Directory**: `dist` (default for Vite)
3. Add environment variable:
   - `VITE_API_URL` = `https://swasthyasetu-backend.onrender.com` (your Render URL from C.2, **no trailing slash**)
4. Click **Deploy**. Vercel gives you a URL like
   `https://swasthyasetu-ai.vercel.app`.
5. Go back to Render (step C.2.4) and set `ALLOWED_ORIGINS` to this exact
   Vercel URL, then trigger a redeploy on Render so CORS allows it.

### C.4 — Final check

Open your Vercel URL, send a test symptom, and confirm you get a full
follow-up flow with citations. Test the emergency path too ("chest pain
and can't breathe") so you know it works live before judges try it.

### C.5 — Verify the offline/PWA features on the deployed site

The offline engine and service worker only fully prove themselves on a
real HTTPS deployment (service workers require HTTPS or `localhost`) —
Vercel gives you HTTPS automatically, so this is the right point to test:

1. Open the deployed Vercel URL once (this lets the service worker
   install and cache the app shell — check DevTools → Application →
   Service Workers to confirm it registered).
2. Open DevTools → Network tab → set throttling to **Offline**.
3. Reload the page — it should still load (that's the PWA app-shell cache).
4. Send a symptom message — it should still get a fully cited answer
   (that's the client-side offline engine in `src/offline/`), and you
   should see the amber "offline" banner.
5. Turn throttling back to **Online** — within a few seconds the app
   attempts a background sync of the offline transcript to
   `POST /api/sync` (check the Network tab or the Render backend logs).

If step 3 fails (blank page offline), the service worker likely didn't
get a chance to install before you went offline — reload once while
online first, then retry.

> **Monorepo note:** `frontend/scripts/sync-knowledge-base.js` (which runs
> automatically via the `prebuild` npm script) copies
> `backend/app/data/*.json` into `frontend/src/offline/` using a path
> relative to the script's own location, not the current working
> directory — so it works correctly on Vercel even though Vercel's "Root
> Directory" setting changes the build's working directory to `frontend/`.
> It does need the full repo checked out (which Vercel does by default
> for a connected GitHub repo), so don't set up the frontend as a
> separate, backend-less repo unless you also commit a static copy of
> those two JSON files directly into `frontend/src/offline/`.

---

## CI/CD with GitHub Actions

Two workflows are included under `.github/workflows/`:

- `backend-ci.yml` — installs dependencies and runs `pytest` on every
  push/PR touching `backend/**`.
- `frontend-ci.yml` — installs dependencies and runs `npm run build` on
  every push/PR touching `frontend/**`, catching build breaks before they
  reach `main`.

Both Render and Vercel also auto-deploy on every push to `main` once
connected (steps C.2/C.3 above set this up by default) — so once this is
wired up, your public demo URL updates automatically as you keep
committing during the hackathon.

---

## Environment variables reference

### Backend (`backend/.env`)

| Variable | Required? | Default | Purpose |
|---|---|---|---|
| `ALLOWED_ORIGINS` | Recommended in prod | `http://localhost:5173,http://127.0.0.1:5173` | CORS allow-list |
| `RETRIEVAL_THRESHOLD` | No | `0.08` | Minimum similarity score to accept a topic match |
| `TOP_K_RESULTS` | No | `2` | How many topics to consider internally |
| `BHASHINI_USER_ID` / `BHASHINI_API_KEY` / `BHASHINI_PIPELINE_ID` | No | empty | Enables server-side Hindi ASR/TTS via Bhashini (bonus) |
| `ANTHROPIC_API_KEY` | No | empty | Enables optional LLM-phrased answers (see ARCHITECTURE.md) |

### Frontend (`frontend/.env`)

| Variable | Required? | Default | Purpose |
|---|---|---|---|
| `VITE_API_URL` | Yes | `http://localhost:8000` | Base URL of the backend API |

---

## Setting up the Bhashini voice bonus (optional)

The app works fully without this — the browser's Web Speech API handles
voice input by default. To upgrade to Bhashini's government ASR/TTS models
for more accurate Hindi recognition:

1. Register at https://bhashini.gov.in (free developer tier).
2. Create a pipeline for ASR (`hi`) and note your `userID`, `ulcaApiKey`,
   and the `pipelineId` for the Hindi ASR service.
3. Set `BHASHINI_USER_ID`, `BHASHINI_API_KEY`, `BHASHINI_PIPELINE_ID` in
   `backend/.env` (or your Render environment variables).
4. Restart the backend — `config.BHASHINI_ENABLED` will flip to `True`
   automatically, and `/api/voice/transcribe` becomes available.
5. Wire the frontend's `VoiceButton.jsx` to call that endpoint instead of
   (or as a fallback path from) the Web Speech API — see the comment block
   at the top of that file for exactly where to swap it in.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Frontend shows "Could not reach the SwasthyaSetu server" | Backend not running, or wrong `VITE_API_URL` | Check `curl <backend-url>/api/health`; fix `.env` and restart `npm run dev` |
| CORS error in browser console | `ALLOWED_ORIGINS` on backend doesn't include your frontend's exact URL | Update `ALLOWED_ORIGINS` and redeploy backend |
| Render free instance is slow to respond first time | Free tier spins down after inactivity | Hit `/api/health` ~1 min before demoing |
| `pytest` fails on `ModuleNotFoundError` | Virtual env not activated / deps not installed | `source venv/bin/activate && pip install -r requirements.txt` |
| Mic button does nothing | Browser doesn't support `SpeechRecognition`, or no mic permission | Use Chrome/Edge; check the browser's site permissions |
