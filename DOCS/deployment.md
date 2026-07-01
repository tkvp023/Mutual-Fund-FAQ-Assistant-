# Deployment Guide

> **Backend:** Railway (Python + FastAPI)
> **Frontend:** Vercel (Next.js)

---

## Architecture

```
┌─────────────────────┐         ┌─────────────────────────┐
│   Vercel (Frontend)  │ ──────► │   Railway (Backend API)  │
│   Next.js App        │  HTTPS  │   FastAPI + RAG Pipeline │
│   Port: auto         │         │   Port: $PORT (auto)     │
│                     │         │                         │
│   Env:              │         │   Env:                  │
│   NEXT_PUBLIC_API_URL│         │   GROQ_API_KEY          │
│                     │         │   ALLOWED_ORIGINS       │
│                     │         │   CHROMA_PERSIST_DIR    │
└─────────────────────┘         └─────────────────────────┘
```

---

## Step 1: Push to GitHub

Make sure both the backend (root) and frontend (`/frontend`) are in the **same repo**.

```bash
git add -A
git commit -m "prepare for Railway + Vercel deployment"
git push origin main
```

---

## Step 2: Deploy Backend on Railway

### 2.1 Create a New Project

1. Go to [railway.app](https://railway.app) and sign in with GitHub.
2. Click **"New Project"** → **"Deploy from GitHub Repo"**.
3. Select your `RAG-based Mutual Fund FAQ Chatbot` repo.

### 2.2 Configure Root Directory

Railway will auto-detect the Python project from the root. The `railway.json` and `Procfile` are already configured:

- **Start command:** `uvicorn app.api:app --host 0.0.0.0 --port $PORT`
- **Health check:** `/api/health` (120s timeout for model loading)
- **Python version:** `3.12.0` (pinned in `runtime.txt`)

### 2.3 Set Environment Variables

Go to **Settings → Variables** and add:

| Variable | Value | Required |
|---|---|---|
| `GROQ_API_KEY` | Your Groq API key from [console.groq.com](https://console.groq.com) | ✅ Yes |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Optional (has default) |
| `ALLOWED_ORIGINS` | `https://your-app.vercel.app` (fill in after Vercel deploy) | ✅ Yes |
| `CHROMA_PERSIST_DIR` | `/data/chroma_db` (if using a volume, see below) | Optional |

### 2.4 Add a Persistent Volume (Important!)

Railway containers are **ephemeral** — without a volume, ChromaDB data is lost on every redeploy.

1. In your Railway service, go to **Settings → Volumes**.
2. Click **"Add Volume"**.
3. Set **Mount Path** to `/data`.
4. Set the env var `CHROMA_PERSIST_DIR=/data/chroma_db`.

> [!WARNING]
> Without a volume, you'll need to re-run the ingestion pipeline after every deploy.
> If the volume isn't available, the default `./chroma_db` path works but data won't persist across deploys.

### 2.5 Run Ingestion on Railway

After the first deploy, you need to populate ChromaDB. You have two options:

**Option A: Use Railway CLI (recommended)**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Link to your project
railway link

# Run ingestion as a one-off command
railway run python -m pipeline.ingest
```

**Option B: Include chroma_db in the repo**

If the dataset is small (ours is ~200KB), you can commit the `chroma_db/` folder:
```bash
# Remove chroma_db/ from .gitignore temporarily
git add chroma_db/
git commit -m "include pre-built vector store"
git push
```

> [!TIP]
> Option B is simpler for this project since the ChromaDB is only ~200KB (128 chunks × 384 dims).

### 2.6 Verify Backend is Live

Once deployed, Railway gives you a public URL like `https://your-app.up.railway.app`.

Test it:
```bash
curl https://your-app.up.railway.app/api/health
# Should return: {"status":"ok","pipeline_loaded":true,"chunks_in_db":128,...}
```

Also check: `https://your-app.up.railway.app/docs` for Swagger UI.

### 2.7 Generate a Public Domain (Optional)

By default Railway gives you a `*.up.railway.app` URL. You can also:
- Go to **Settings → Networking → Generate Domain** to get a cleaner URL.
- Or add a custom domain.

**Copy your Railway URL** — you'll need it for the Vercel deployment.

---

## Step 3: Deploy Frontend on Vercel

### 3.1 Import Project

1. Go to [vercel.com](https://vercel.com) and sign in with GitHub.
2. Click **"Add New Project"** → **Import** your repo.
3. **Set Root Directory** to `frontend` (critical! — the Next.js app lives in `/frontend`).

### 3.2 Configure Build Settings

Vercel should auto-detect Next.js. Verify:

| Setting | Value |
|---|---|
| **Framework Preset** | Next.js |
| **Root Directory** | `frontend` |
| **Build Command** | `npm run build` (default) |
| **Output Directory** | `.next` (default) |

### 3.3 Set Environment Variables

Add this in Vercel's **Settings → Environment Variables**:

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://your-app.up.railway.app` (your Railway backend URL) |

> [!IMPORTANT]
> The `NEXT_PUBLIC_` prefix is required — it makes the variable available in the browser.
> Do NOT include a trailing slash in the URL.

### 3.4 Deploy

Click **"Deploy"**. Vercel will:
1. Install dependencies (`npm install`)
2. Build the Next.js app (`npm run build`)
3. Deploy to their edge network

### 3.5 Verify Frontend is Live

Open your Vercel URL (e.g. `https://your-app.vercel.app`) and:
1. The chat UI should load with the dark glassmorphism theme.
2. Click a suggested question — it should hit the Railway backend and return an answer.

---

## Step 4: Connect Frontend ↔ Backend

After both are deployed, you need to tell each service about the other:

### 4.1 Update Railway CORS

Go to your Railway service → **Variables** and set:
```
ALLOWED_ORIGINS=https://your-app.vercel.app
```

If you have a custom domain too:
```
ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-custom-domain.com
```

Railway will auto-redeploy after changing env vars.

### 4.2 Verify End-to-End

1. Open your Vercel URL.
2. Type a question like "What is the NAV of HDFC Mid Cap Fund?"
3. You should see the typing indicator, then an answer with source cards.

---

## Troubleshooting

### "Failed to fetch" / CORS errors in browser console

- **Cause:** The frontend URL isn't in Railway's `ALLOWED_ORIGINS`.
- **Fix:** Add your exact Vercel URL (with `https://`, no trailing slash) to `ALLOWED_ORIGINS` in Railway.

### Backend health check fails / times out

- **Cause:** The BGE model takes 30-60s to download on first cold start.
- **Fix:** The `railway.json` has a 120s health check timeout. If it's still failing, increase it or check the deploy logs.

### "Pipeline not ready" (503 error)

- **Cause:** The backend is still loading the BGE embedding model.
- **Fix:** Wait 30-60 seconds and retry. This only happens on cold starts.

### ChromaDB is empty (0 chunks)

- **Cause:** The ingestion pipeline hasn't been run on Railway.
- **Fix:** Either commit `chroma_db/` to the repo, or run `railway run python -m pipeline.ingest`.

### Frontend shows stale API URL

- **Cause:** `NEXT_PUBLIC_API_URL` is baked in at build time in Next.js.
- **Fix:** After changing the env var in Vercel, trigger a **redeploy** (Settings → Deployments → Redeploy).

---

## Cost Estimates

| Service | Free Tier | Notes |
|---|---|---|
| **Railway** | $5/month credit (Hobby) | BGE model uses ~200MB RAM; Groq calls are external |
| **Vercel** | Free (Hobby) | Static/SSR Next.js, generous bandwidth |
| **Groq** | Free tier | ~14,400 requests/day on free plan |

---

## Environment Variables Summary

### Railway (Backend)
```env
GROQ_API_KEY=gsk_...                          # Required
GROQ_MODEL=llama-3.1-8b-instant              # Optional
ALLOWED_ORIGINS=https://your-app.vercel.app   # Required
CHROMA_PERSIST_DIR=/data/chroma_db            # If using volume
```

### Vercel (Frontend)
```env
NEXT_PUBLIC_API_URL=https://your-app.up.railway.app   # Required
```
