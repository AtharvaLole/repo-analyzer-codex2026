# AI-Powered Software Engineering Assistant

Production-grade monorepo scaffold for a repository analysis assistant using FastAPI, CrewAI, LangGraph, ChromaDB, Redis, Celery, Next.js, Tailwind CSS, and Clerk.

## Structure

- `backend/`: FastAPI API, agent layer, LangGraph workflow, RAG indexing, Redis cache, Celery tasks, tests, and Dockerfile.
- `frontend/`: Next.js 14 App Router UI, Clerk wrapper, Tailwind styling, typed API client, and Dockerfile.
- `.github/workflows/`: CI and deployment workflows for GitHub Actions.
- `docker-compose.yml`: Local Redis, backend, worker, and frontend services.
- `docker-compose.prod.yml`: Production-style backend, worker, and Redis services.

## Local Development

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Docker Compose:

```bash
docker compose up --build
```

The API runs on `http://localhost:8000` and the frontend runs on `http://localhost:3000`.

## Environment

Copy the example files before running locally:

- `backend/.env.example` to `backend/.env`
- `frontend/.env.example` to `frontend/.env.local`

Secrets such as `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `CLERK_SECRET_KEY`, and `SENTRY_DSN` are intentionally empty in example files.

## Backend Notes

The backend uses Pydantic v2 settings, async FastAPI endpoints, a ChromaDB-backed retriever, BM25 keyword scoring, Redis helpers, Celery task scaffolding, CrewAI crew builders, and a LangGraph workflow assembly. The RAG chunker is line-aware and ready for language-specific Tree-sitter grammar integration.

## Frontend Notes

The frontend starts at `/dashboard` and includes repository indexing, agent status, repository chat, code citations, and README generation screens. Clerk is wired at the root layout so authentication can be enforced as routes mature.

## CI/CD

`ci.yml` installs backend and frontend dependencies, runs backend tests, and builds the frontend. `deploy.yml` is configured for Railway and Vercel using GitHub Secrets.
