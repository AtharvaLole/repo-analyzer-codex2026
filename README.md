# AI-Powered Repo Analyzer

Local demo app for analyzing GitHub repositories with FastAPI, Redis, ChromaDB, and a Next.js interface.

This version is intentionally optimized for running in front of judges. Docker, deployment workflows, and production hosting files have been removed.

## What Runs

- Backend API: `http://localhost:8000`
- Frontend UI: `http://localhost:3000`
- Redis: `localhost:6379`
- FastAPI background tasks: indexing and README jobs

## Demo Behavior

The app can index repositories locally without an OpenAI key. If `OPENAI_API_KEY` is missing, it uses deterministic local embeddings and local citation-based answers so the demo does not get stuck during indexing.

Set `OPENAI_API_KEY` only when you want full cloud LLM reasoning.

## Backend

Use Python 3.11.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install --use-deprecated=legacy-resolver -r requirements.txt
$env:DEBUG="true"
$env:REDIS_URL="redis://localhost:6379/0"
$env:CHROMA_PERSIST_DIR=".data/chroma"
$env:REPOS_BASE_DIR=".data/repos"
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev -- -p 3000
```

## Redis

Run any local Redis server on port `6379`. This workspace also supports the portable Windows Redis binary under `.tools/redis-windows` if present:

```powershell
.\.tools\redis-windows\redis-server.exe --port 6379
```

## Quick Check

```powershell
Invoke-WebRequest http://localhost:8000/health
Invoke-WebRequest http://localhost:3000
```

Then open `http://localhost:3000`, paste a GitHub repo URL, and wait for indexing to complete.
