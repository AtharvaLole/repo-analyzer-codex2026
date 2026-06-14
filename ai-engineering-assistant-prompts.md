# AI-Powered Software Engineering Assistant
## Step-by-Step Build Prompts for AI Code Editor
### Production-Grade with Deployment

---

> **How to use this guide**
> Feed each numbered prompt block into your AI code editor (Cursor, Windsurf, etc.) one at a time.
> Wait for each step to complete and verify before moving to the next.
> Each prompt is self-contained but builds on the previous step.

---

## Tech Stack Reference

| Layer | Technology |
|---|---|
| Backend framework | FastAPI (Python 3.11+) |
| Agent orchestration | CrewAI |
| Workflow state machine | LangGraph |
| LLM provider | OpenAI GPT-4o / Anthropic Claude |
| Vector database | ChromaDB (persistent) |
| Keyword search | BM25 via `rank_bm25` |
| Cache layer | Redis 7 |
| Code parsing | Tree-sitter + GitPython |
| Static analysis | Semgrep + Bandit |
| Frontend | Next.js 14 (App Router) + Tailwind CSS |
| Auth | Clerk |
| Background jobs | Celery + Redis as broker |
| Containerisation | Docker + Docker Compose |
| Deployment | Railway (backend) + Vercel (frontend) |
| Monitoring | Sentry + Loguru |
| CI/CD | GitHub Actions |

---

## PHASE 1 — Project Scaffold & Environment

---

### PROMPT 1 — Repository structure and base config

```
Create a production-grade monorepo with the following structure:

/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py               # FastAPI app entry point
│   │   ├── config.py             # Pydantic Settings with env vars
│   │   ├── dependencies.py       # FastAPI dependency injection
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── router.py     # Aggregates all v1 routes
│   │   │   │   ├── repos.py      # /repos endpoints
│   │   │   │   ├── chat.py       # /chat endpoints
│   │   │   │   ├── readme.py     # /readme endpoints
│   │   │   │   └── agents.py     # /agents status endpoints
│   │   ├── agents/
│   │   │   ├── __init__.py
│   │   │   ├── orchestrator.py
│   │   │   ├── retrieval_agent.py
│   │   │   ├── code_analysis_agent.py
│   │   │   ├── security_agent.py
│   │   │   ├── test_gen_agent.py
│   │   │   ├── readme_agent.py
│   │   │   ├── dependency_agent.py
│   │   │   └── review_agent.py
│   │   ├── crews/
│   │   │   ├── __init__.py
│   │   │   ├── indexing_crew.py
│   │   │   ├── readme_crew.py
│   │   │   └── qa_crew.py
│   │   ├── graph/
│   │   │   ├── __init__.py
│   │   │   ├── state.py          # LangGraph state definitions
│   │   │   ├── nodes.py          # LangGraph node functions
│   │   │   └── workflow.py       # LangGraph graph assembly
│   │   ├── rag/
│   │   │   ├── __init__.py
│   │   │   ├── indexer.py        # Repo cloning + chunking
│   │   │   ├── embedder.py       # Embedding + ChromaDB writes
│   │   │   ├── retriever.py      # Hybrid search (vector + BM25)
│   │   │   └── chunker.py        # Tree-sitter based chunking
│   │   ├── cache/
│   │   │   ├── __init__.py
│   │   │   └── redis_client.py   # Redis connection + helpers
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── request.py        # Pydantic request models
│   │   │   └── response.py       # Pydantic response models
│   │   ├── tasks/
│   │   │   ├── __init__.py
│   │   │   └── celery_app.py     # Celery setup + task definitions
│   │   └── utils/
│   │       ├── __init__.py
│   │       ├── logger.py         # Loguru setup
│   │       └── github.py         # GitPython helpers
│   ├── tests/
│   │   ├── __init__.py
│   │   ├── test_api.py
│   │   ├── test_rag.py
│   │   └── test_agents.py
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .env.example
│   └── pyproject.toml
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   ├── dashboard/
│   │   │   └── page.tsx
│   │   ├── repo/
│   │   │   └── [repoId]/
│   │   │       ├── page.tsx
│   │   │       ├── chat/
│   │   │       │   └── page.tsx
│   │   │       └── readme/
│   │   │           └── page.tsx
│   ├── components/
│   │   ├── ui/                   # shadcn/ui components
│   │   ├── RepoInput.tsx
│   │   ├── ChatWindow.tsx
│   │   ├── AgentStatusPanel.tsx
│   │   ├── ReadmePreview.tsx
│   │   └── CodeCitation.tsx
│   ├── lib/
│   │   ├── api.ts                # Axios client
│   │   └── types.ts              # Shared TypeScript types
│   ├── public/
│   ├── Dockerfile
│   ├── package.json
│   └── next.config.ts
├── docker-compose.yml
├── docker-compose.prod.yml
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── deploy.yml
└── README.md

Rules:
- Use Python 3.11 with strict type hints everywhere in backend
- Use Pydantic v2 for all data models
- All async endpoints using async/await
- Environment variables via python-dotenv + pydantic-settings
- Never hardcode secrets
- Add __all__ exports to every __init__.py

Create all files with correct content, including a requirements.txt with these pinned packages:
fastapi==0.111.0
uvicorn[standard]==0.29.0
pydantic==2.7.1
pydantic-settings==2.2.1
crewai==0.30.11
langgraph==0.0.55
langchain==0.1.20
langchain-openai==0.1.7
langchain-anthropic==0.1.11
chromadb==0.5.0
rank-bm25==0.2.2
gitpython==3.1.43
tree-sitter==0.22.3
semgrep==1.72.0
bandit==1.7.8
redis==5.0.4
celery==5.4.0
httpx==0.27.0
python-multipart==0.0.9
loguru==0.7.2
sentry-sdk[fastapi]==2.3.1
pytest==8.2.0
pytest-asyncio==0.23.6
```

---

### PROMPT 2 — Config, logging, and Redis client

```
In backend/app/config.py, implement a Pydantic Settings class that loads:
- OPENAI_API_KEY
- ANTHROPIC_API_KEY
- REDIS_URL (default: redis://localhost:6379)
- CHROMA_PERSIST_DIR (default: ./chroma_db)
- REPOS_BASE_DIR (default: ./repos)
- CELERY_BROKER_URL (same as REDIS_URL)
- CELERY_RESULT_BACKEND (same as REDIS_URL)
- SENTRY_DSN (optional)
- ENVIRONMENT (default: development)
- MAX_REPO_SIZE_MB (default: 500)
- EMBEDDING_MODEL (default: text-embedding-3-small)
- LLM_MODEL (default: gpt-4o)
- LOG_LEVEL (default: INFO)

Use model_config = SettingsConfigDict(env_file=".env", extra="ignore")

In backend/app/utils/logger.py:
- Set up Loguru with structured JSON output in production
- Plain coloured output in development
- Log rotation at 50MB, retention 10 days
- Expose a get_logger(name) function

In backend/app/cache/redis_client.py:
- Create a RedisClient class using redis.asyncio
- Implement these methods with type hints:
  - async get(key: str) -> str | None
  - async set(key: str, value: str, ttl_seconds: int = 3600) -> None
  - async delete(key: str) -> None
  - async exists(key: str) -> bool
  - async get_json(key: str) -> dict | None
  - async set_json(key: str, value: dict, ttl_seconds: int = 3600) -> None
- Use connection pooling
- Add a health_check() method
- Expose a get_redis() dependency for FastAPI injection

TTL strategy:
- Embedding cache: 86400 (24h)
- RAG query cache: 3600 (1h)  
- Agent output cache (README, full reports): keyed by {repo_id}:{commit_sha}, TTL 604800 (7 days)
- Session/user data: 1800 (30min)
```

---

## PHASE 2 — RAG Pipeline

---

### PROMPT 3 — Repository indexing and Tree-sitter chunking

```
In backend/app/rag/chunker.py, implement a CodeChunker class:

Use tree-sitter to parse files. Support these languages with their file extensions:
- Python (.py)
- JavaScript (.js, .jsx)
- TypeScript (.ts, .tsx)
- Java (.java)
- Go (.go)
- Rust (.rs)
- C/C++ (.c, .cpp, .h)
- Ruby (.rb)

For each supported file, extract chunks at function and class level:
- Each chunk: {"content": str, "file_path": str, "start_line": int, "end_line": int, "chunk_type": "function"|"class"|"module", "language": str, "name": str}
- If tree-sitter parsing fails, fall back to sliding window chunking (512 tokens, 64 token overlap)
- For unsupported files (markdown, yaml, json, txt), use sliding window with 256 tokens

In backend/app/rag/indexer.py, implement a RepoIndexer class:
- clone_repo(github_url: str, repo_id: str) -> Path
  - Use GitPython to clone into REPOS_BASE_DIR/{repo_id}
  - If already cloned, do a git pull instead
  - Validate repo size against MAX_REPO_SIZE_MB
  - Return the local path
- get_commit_sha(repo_path: Path) -> str
  - Return current HEAD commit SHA
- list_files(repo_path: Path) -> list[Path]
  - Walk all files, exclude: .git, node_modules, __pycache__, .venv, dist, build, *.min.js, *.lock, *.png, *.jpg, *.pdf
- index_repo(repo_id: str, github_url: str) -> IndexResult
  - Clone or pull repo
  - List all files
  - Chunk every file using CodeChunker
  - Return IndexResult with: {repo_id, commit_sha, total_files, total_chunks, file_list}

IndexResult should be a Pydantic model.
Add comprehensive error handling with custom exceptions: RepoTooLargeError, CloneFailedError, IndexingError
```

---

### PROMPT 4 — Embedder and ChromaDB integration

```
In backend/app/rag/embedder.py, implement a CodeEmbedder class:

Use OpenAI text-embedding-3-small for embeddings.

Methods:
- async embed_texts(texts: list[str]) -> list[list[float]]
  - Batch in groups of 100 to avoid rate limits
  - Check Redis cache first using key: emb:{sha256(text)[:16]}
  - Cache each embedding with TTL 86400
  - Return list of embedding vectors

- async index_chunks(repo_id: str, chunks: list[dict], commit_sha: str) -> None
  - Get or create a ChromaDB collection named repo_{repo_id}
  - Embed all chunk content in batches
  - Upsert into ChromaDB with metadata: {file_path, start_line, end_line, chunk_type, language, name, commit_sha}
  - Use chunk ID: {repo_id}:{file_path}:{start_line}
  - Store the commit_sha in Redis: repo:{repo_id}:commit_sha

- async delete_repo_index(repo_id: str) -> None
  - Delete the ChromaDB collection for this repo

Use chromadb.PersistentClient with path from settings.CHROMA_PERSIST_DIR.

In backend/app/rag/retriever.py, implement a HybridRetriever class:

- async semantic_search(repo_id: str, query: str, top_k: int = 10) -> list[SearchResult]
  - Embed the query
  - Query ChromaDB collection for repo_{repo_id}
  - Return top_k results with score

- async bm25_search(repo_id: str, query: str, top_k: int = 10) -> list[SearchResult]
  - Load all documents for this repo from ChromaDB (or maintain a BM25 index in Redis)
  - Use rank_bm25 BM25Okapi
  - Return top_k results with score

- async hybrid_search(repo_id: str, query: str, top_k: int = 8) -> list[SearchResult]
  - Run semantic_search and bm25_search in parallel using asyncio.gather
  - Merge using Reciprocal Rank Fusion: score = sum(1/(k+rank)) for k=60
  - Deduplicate by chunk ID
  - Return top_k merged and re-ranked results
  - Cache result in Redis with key: hybrid:{repo_id}:{sha256(query)[:12]}, TTL 3600

SearchResult Pydantic model:
{
  chunk_id: str,
  content: str,
  file_path: str,
  start_line: int,
  end_line: int,
  chunk_type: str,
  language: str,
  name: str,
  score: float,
  search_type: Literal["semantic", "bm25", "hybrid"]
}
```

---

## PHASE 3 — CrewAI Agents

---

### PROMPT 5 — Base agent setup and LLM configuration

```
In backend/app/agents/__init__.py, set up shared LLM instances:

Create two LLM instances:
1. llm_fast: ChatOpenAI with model="gpt-4o-mini", temperature=0, max_tokens=2000
   - Used for retrieval decisions, quick classification
2. llm_powerful: ChatOpenAI with model="gpt-4o", temperature=0.1, max_tokens=4000
   - Used for code analysis, README generation, security review

Also create a Claude fallback:
3. llm_claude: ChatAnthropic with model="claude-sonnet-4-6", temperature=0.1
   - Used as fallback if OpenAI rate limits hit

Create a base Agent factory function make_agent(role, goal, backstory, tools, llm) that:
- Sets verbose=False in production, True in development
- Sets max_iter=5 to prevent runaway loops
- Sets memory=False (we manage memory via Redis ourselves)
- Returns a crewai.Agent

Create a Tool registry in backend/app/agents/tools.py:

Implement these as @tool decorated functions:
1. search_codebase(query: str, repo_id: str) -> str
   - Calls HybridRetriever.hybrid_search
   - Formats results as: FILE: {path} (lines {start}-{end})\n{content}

2. read_file(file_path: str, repo_id: str) -> str
   - Reads file from REPOS_BASE_DIR/{repo_id}/{file_path}
   - Returns content truncated to 8000 chars with line numbers

3. run_semgrep(repo_id: str) -> str
   - Runs: semgrep --config=auto --json {repo_path}
   - Parses JSON output, returns formatted findings

4. run_bandit(repo_id: str) -> str
   - Runs: bandit -r {repo_path} -f json
   - Parses output, returns formatted findings

5. list_repo_files(repo_id: str) -> str
   - Lists all indexed files with their languages and sizes

6. get_repo_structure(repo_id: str) -> str
   - Returns directory tree up to 3 levels deep as ASCII tree
```

---

### PROMPT 6 — All 8 CrewAI agents

```
Implement all 8 agents in backend/app/agents/. Each file should export a function that takes (repo_id: str) and returns a crewai.Agent.

backend/app/agents/retrieval_agent.py
- Role: "Senior Codebase Retrieval Specialist"
- Goal: "Find the most relevant code chunks for any query using hybrid search"
- Backstory: "Expert at semantic and keyword search over large codebases. Always cites exact file paths and line numbers."
- Tools: [search_codebase, list_repo_files]
- LLM: llm_fast

backend/app/agents/code_analysis_agent.py
- Role: "Senior Software Engineer"
- Goal: "Deeply understand code logic, architecture patterns, and implementation details"
- Backstory: "10+ years reading production code. Explains complex systems simply. Always references the actual code, never makes assumptions."
- Tools: [search_codebase, read_file, get_repo_structure]
- LLM: llm_powerful

backend/app/agents/security_agent.py
- Role: "Application Security Engineer"
- Goal: "Identify security vulnerabilities, check OWASP Top 10, detect hardcoded secrets, SQL injection, XSS, insecure auth"
- Backstory: "Former penetration tester. Runs static analysis tools and reviews code logic for security flaws."
- Tools: [run_semgrep, run_bandit, read_file, search_codebase]
- LLM: llm_powerful

backend/app/agents/dependency_agent.py
- Role: "Systems Architect"
- Goal: "Map function call chains, module dependencies, and data flow through the codebase"
- Backstory: "Specialist in understanding how code flows from entry points through layers to the database."
- Tools: [search_codebase, read_file, get_repo_structure]
- LLM: llm_powerful

backend/app/agents/test_gen_agent.py
- Role: "Senior QA Engineer"
- Goal: "Generate comprehensive unit and integration tests with edge cases"
- Backstory: "Writes tests that actually catch bugs. Understands pytest, Jest, and JUnit idioms deeply."
- Tools: [search_codebase, read_file]
- LLM: llm_powerful

backend/app/agents/readme_agent.py
- Role: "Technical Documentation Writer"
- Goal: "Generate a production-quality README with architecture overview, setup guide, API reference, and usage examples"
- Backstory: "Has written docs for open-source projects with 10k+ GitHub stars. Makes complex projects approachable."
- Tools: [search_codebase, read_file, get_repo_structure, list_repo_files]
- LLM: llm_powerful

backend/app/agents/refactor_agent.py
- Role: "Code Quality Engineer"
- Goal: "Identify code smells, duplicate logic, and suggest concrete refactoring improvements"
- Backstory: "Deep knowledge of SOLID principles, design patterns, and clean code. Always shows before/after."
- Tools: [search_codebase, read_file]
- LLM: llm_powerful

backend/app/agents/review_agent.py
- Role: "Principal Engineer (Reviewer)"
- Goal: "Review all agent outputs for accuracy, correctness, and quality before delivery"
- Backstory: "Final quality gate. Checks that all claims are grounded in actual code, not hallucinations. Adds confidence scores."
- Tools: [search_codebase, read_file]
- LLM: llm_powerful
```

---

### PROMPT 7 — CrewAI Crews

```
Implement three Crew classes in backend/app/crews/.

backend/app/crews/indexing_crew.py
IndexingCrew class with method:
  async run(repo_id: str, github_url: str) -> IndexResult
  - Steps (sequential, not using CrewAI for this one — direct pipeline):
    1. RepoIndexer.clone_repo(github_url, repo_id)
    2. RepoIndexer.index_repo to get chunks
    3. CodeEmbedder.index_chunks to write to ChromaDB
    4. Store metadata in Redis: repo:{repo_id}:meta = {url, commit_sha, indexed_at, file_count, chunk_count}
    5. Return IndexResult

backend/app/crews/readme_crew.py
ReadmeCrew class with method:
  async run(repo_id: str) -> ReadmeResult
  - Cache check: Redis key readme:{repo_id}:{commit_sha} — return cached if exists
  - Create agents: code_analysis_agent, dependency_agent, readme_agent, review_agent
  - Create Tasks:
    Task 1 (code_analysis_agent): "Analyse the overall architecture, key modules, tech stack, and entry points of repo {repo_id}. List every major component with its file path."
    Task 2 (dependency_agent): "Map the dependency graph and main data flows. Describe the request lifecycle from entry point to response."
    Task 3 (readme_agent): "Using the analysis, generate a complete README.md with these sections: Project Title, Description, Architecture Overview (with mermaid diagram), Tech Stack, Prerequisites, Installation, Configuration, Usage, API Reference, Project Structure, Contributing, License"
    Task 4 (review_agent): "Review the README for accuracy against the actual code. Fix any incorrect claims. Add a confidence score (0-100)."
  - Run as sequential Crew
  - Cache result: readme:{repo_id}:{commit_sha} TTL 604800
  - Return ReadmeResult {content: str, confidence: int, sections: list[str]}

backend/app/crews/qa_crew.py
QACrew class with method:
  async run(repo_id: str, question: str) -> QAResult
  - Cache check: Redis key qa:{repo_id}:{sha256(question)[:16]} — return cached if exists
  - Create agents: retrieval_agent, code_analysis_agent, review_agent
  - Tasks:
    Task 1 (retrieval_agent): "Find all code relevant to this question: '{question}' in repo {repo_id}. Return file paths, line numbers, and content."
    Task 2 (code_analysis_agent): "Using the retrieved code, answer this question with precision: '{question}'. Cite every claim with file:line references."
    Task 3 (review_agent): "Verify the answer is grounded in the actual code. Add a confidence score and flag any uncertain claims."
  - Run as sequential Crew
  - Cache result TTL 3600
  - Return QAResult {answer: str, citations: list[Citation], confidence: int}

Citation model: {file_path: str, start_line: int, end_line: int, snippet: str, relevance: str}
```

---

## PHASE 4 — LangGraph Workflow

---

### PROMPT 8 — LangGraph state and workflow

```
In backend/app/graph/state.py, define the AgentState TypedDict:

from typing import TypedDict, Literal, Annotated
import operator

class AgentState(TypedDict):
    repo_id: str
    user_query: str
    intent: Literal["qa", "readme", "security", "tests", "refactor", "explain", "unknown"]
    retrieval_results: list[dict]
    code_analysis: str
    security_findings: list[dict]
    agent_outputs: Annotated[list[str], operator.add]
    final_answer: str
    citations: list[dict]
    confidence: int
    error: str | None
    active_agents: list[str]
    completed_steps: Annotated[list[str], operator.add]

In backend/app/graph/nodes.py, implement these async node functions:

1. intent_router(state: AgentState) -> AgentState
   - Use llm_fast to classify the query into one of the intent literals
   - Prompt: "Classify this query into exactly one category: qa, readme, security, tests, refactor, explain, unknown. Query: {query}. Respond with only the category word."
   - Update state["intent"] and state["active_agents"]

2. retrieval_node(state: AgentState) -> AgentState
   - Call HybridRetriever.hybrid_search
   - Update state["retrieval_results"]
   - Append "retrieval" to completed_steps

3. code_analysis_node(state: AgentState) -> AgentState
   - Run QACrew if intent is qa/explain
   - Update state["code_analysis"] and state["citations"]

4. security_node(state: AgentState) -> AgentState
   - Run security_agent
   - Update state["security_findings"]

5. readme_node(state: AgentState) -> AgentState
   - Run ReadmeCrew
   - Update state["final_answer"]

6. review_node(state: AgentState) -> AgentState
   - Aggregate all agent outputs
   - Run review_agent for final quality check
   - Update state["final_answer"] and state["confidence"]

7. error_node(state: AgentState) -> AgentState
   - Log the error
   - Set a user-friendly error message in state["final_answer"]

In backend/app/graph/workflow.py:

Build the StateGraph:
- Add all nodes
- Set entry point: intent_router
- Add conditional edges from intent_router:
  - "qa" or "explain" -> retrieval_node
  - "readme" -> readme_node
  - "security" -> retrieval_node -> security_node -> review_node
  - "tests" -> retrieval_node -> code_analysis_node -> review_node
  - "refactor" -> retrieval_node -> code_analysis_node -> review_node
  - "unknown" -> retrieval_node -> code_analysis_node -> review_node
- readme_node -> END
- review_node -> END
- Add error handling edges

Compile and export: workflow = graph.compile()

Expose: async def run_workflow(repo_id: str, query: str) -> AgentState
```

---

## PHASE 5 — FastAPI Endpoints

---

### PROMPT 9 — All API routes

```
In backend/app/api/v1/repos.py implement:

POST /api/v1/repos/index
  Body: IndexRequest {github_url: str, repo_id: str | None}
  - Validate github_url is a valid GitHub URL
  - Generate repo_id as sha256(github_url)[:12] if not provided
  - Check if already indexed in Redis (repo:{repo_id}:meta)
  - If already indexed and commit matches, return cached IndexResult immediately
  - Otherwise dispatch Celery task: tasks.index_repo.delay(repo_id, github_url)
  - Return: {repo_id: str, task_id: str, status: "queued"}

GET /api/v1/repos/{repo_id}/status
  - Check Redis for repo:{repo_id}:meta
  - Check Celery task status
  - Return: {repo_id, status: "indexing"|"ready"|"failed", meta: dict | None}

GET /api/v1/repos/{repo_id}/files
  - Return list of indexed files from Redis
  - Include: file_path, language, chunk_count

DELETE /api/v1/repos/{repo_id}
  - Delete ChromaDB collection
  - Delete all Redis keys for this repo
  - Delete local repo directory

In backend/app/api/v1/chat.py implement:

POST /api/v1/chat
  Body: ChatRequest {repo_id: str, question: str, stream: bool = False}
  - Verify repo is indexed
  - If stream=True: return StreamingResponse running the workflow and streaming tokens
  - If stream=False: run run_workflow(), return ChatResponse
  ChatResponse: {answer: str, citations: list[Citation], confidence: int, intent: str, active_agents: list[str]}

GET /api/v1/chat/history/{repo_id}
  - Return last 20 Q&A pairs from Redis list: chat:{repo_id}:history

In backend/app/api/v1/readme.py implement:

POST /api/v1/readme/generate
  Body: {repo_id: str, force_regenerate: bool = False}
  - If force_regenerate, delete cache
  - Dispatch Celery task: tasks.generate_readme.delay(repo_id)
  - Return: {task_id: str, status: "queued"}

GET /api/v1/readme/{repo_id}
  - Check Redis for cached README
  - Return: ReadmeResponse {content: str, generated_at: str, confidence: int, format: "markdown"}

In backend/app/api/v1/agents.py implement:

GET /api/v1/agents/status/{task_id}
  - Return Celery task status + progress from Redis
  - Return: {task_id, status, progress: int, current_agent: str, completed_steps: list[str]}

In backend/app/main.py:
- Set up FastAPI with title, version, docs_url
- Include CORS middleware (allow origins from env)
- Include all routers with /api/v1 prefix
- Add startup event: test Redis connection, log ready
- Add /health endpoint returning {status: ok, redis: ok/error, chroma: ok/error}
- Integrate Sentry if SENTRY_DSN is set
- Add request logging middleware using Loguru
```

---

### PROMPT 10 — Celery tasks and background jobs

```
In backend/app/tasks/celery_app.py:

Set up Celery:
- broker = settings.CELERY_BROKER_URL
- result_backend = settings.CELERY_RESULT_BACKEND
- task_serializer = "json"
- result_serializer = "json"
- accept_content = ["json"]
- Enable task routing: indexing tasks to "indexing" queue, readme tasks to "readme" queue

Implement these Celery tasks:

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def index_repo(self, repo_id: str, github_url: str):
  - Update progress in Redis: task:{self.request.id}:progress = {step, percent}
  - Step 1 (10%): Clone/pull repo
  - Step 2 (40%): Chunk all files
  - Step 3 (80%): Embed and index into ChromaDB
  - Step 4 (100%): Store metadata in Redis
  - On failure: retry with exponential backoff
  - On final failure: store error in Redis

@celery_app.task(bind=True, max_retries=2)
def generate_readme(self, repo_id: str):
  - Verify repo is indexed
  - Run ReadmeCrew.run(repo_id)
  - Store result in Redis
  - Update task progress

@celery_app.task
def cleanup_old_repos():
  - Check all repo metadata in Redis
  - Delete repos not accessed in 7 days
  - Schedule this as a periodic task (Celery beat) every 24 hours

Add progress tracking:
- Each task writes to Redis key: task:{task_id}:progress
- Structure: {status, percent, current_step, message, started_at, updated_at}
```

---

## PHASE 6 — Next.js Frontend

---

### PROMPT 11 — Frontend setup and layout

```
Set up the Next.js 14 frontend in /frontend with these specifications:

Install dependencies:
- shadcn/ui (full setup with init)
- @clerk/nextjs for auth
- axios for API calls
- @uiw/react-md-editor for markdown preview
- react-syntax-highlighter for code blocks
- framer-motion for animations
- lucide-react for icons
- @tanstack/react-query for server state
- zustand for client state
- react-hot-toast for notifications

In frontend/lib/api.ts:
- Create an Axios instance with baseURL from NEXT_PUBLIC_API_URL
- Add request interceptor to attach Clerk auth token
- Add response interceptor for global error handling
- Export typed API functions for each endpoint

In frontend/lib/types.ts:
- Mirror all Pydantic response models as TypeScript interfaces
- IndexResult, ChatResponse, Citation, ReadmeResponse, AgentStatus

In frontend/app/layout.tsx:
- ClerkProvider wrapping everything
- React Query Provider
- Toaster
- Inter font from Google Fonts
- Dark mode support via next-themes

Create frontend/app/page.tsx (Landing/Home):
- Hero: "AI-Powered Code Intelligence" 
- Single input: GitHub repo URL
- CTA button: "Analyse Repository"
- On submit: call POST /api/v1/repos/index, redirect to /repo/{repo_id}
- Show 3 feature cards: RAG Q&A, README Generator, Security Scan
- Clean, minimal design using Tailwind

Create frontend/app/dashboard/page.tsx:
- List of previously analysed repos (from localStorage + API)
- Each repo card shows: URL, indexed date, file count, quick action buttons
- Protected by Clerk auth
```

---

### PROMPT 12 — Core UI components

```
Build these React components in frontend/components/:

RepoInput.tsx
- URL input with GitHub URL validation
- Loading state while indexing
- Progress bar showing indexing steps (polling /api/v1/agents/status/{taskId})
- Shows: "Cloning... Parsing files... Embedding... Done!"
- Error state with clear message

AgentStatusPanel.tsx
- Real-time panel showing which agents are active
- Each agent displayed as a pill: idle (gray) | running (blue, pulsing) | done (green)
- Agents: Retrieval, Code Analysis, Security, Test Gen, README Writer, Reviewer
- Shows current step text below
- Animate transitions with framer-motion

ChatWindow.tsx
- Message thread layout (user right, AI left)
- Each AI message includes:
  - Answer text (markdown rendered)
  - Citations accordion: list of {file_path}:{line} chips
  - Confidence badge (green >80, yellow 50-80, red <50)
  - Copy button
- Input box at bottom with send button
- Streaming support: show tokens appearing character by character
- Show AgentStatusPanel while response is loading

CodeCitation.tsx
- Chip showing: filename + line range
- On hover: shows code snippet in a tooltip
- On click: opens full file context in a modal
- Color coded by language (Python=blue, JS=yellow, etc.)

ReadmePreview.tsx
- Split view: raw markdown left, rendered preview right
- Copy to clipboard button
- Download as README.md button
- Confidence indicator
- Regenerate button

Create frontend/app/repo/[repoId]/page.tsx:
- Tabs: Chat | README | Security | Files
- Left sidebar: file tree of indexed repo
- Main area: switches based on active tab
- Show repo metadata header: URL, commit SHA, file count, last indexed

Create frontend/app/repo/[repoId]/chat/page.tsx:
- Full ChatWindow component
- Suggested questions based on repo type (auto-detected)
- Chat history from API

Create frontend/app/repo/[repoId]/readme/page.tsx:
- ReadmePreview component
- Generate button if no README exists yet
- Show generation progress
```

---

## PHASE 7 — Docker & Infrastructure

---

### PROMPT 13 — Docker configuration

```
Create the following Docker files:

backend/Dockerfile:
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    git \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install tree-sitter-languages

COPY . .

RUN mkdir -p /app/repos /app/chroma_db

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

frontend/Dockerfile:
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public
EXPOSE 3000
CMD ["node", "server.js"]

docker-compose.yml (development):
version: "3.9"
services:
  redis:
    image: redis:7-alpine
    ports: ["6379:6379"]
    volumes: [redis_data:/data]
    command: redis-server --appendonly yes

  chromadb:
    image: chromadb/chroma:latest
    ports: ["8001:8000"]
    volumes: [chroma_data:/chroma/chroma]

  backend:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - REDIS_URL=redis://redis:6379
      - CHROMA_PERSIST_DIR=/app/chroma_db
    volumes:
      - ./backend:/app
      - repos_data:/app/repos
      - chroma_data:/app/chroma_db
    depends_on: [redis, chromadb]
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  celery_worker:
    build: ./backend
    command: celery -A app.tasks.celery_app worker --loglevel=info -Q indexing,readme,default --concurrency=2
    environment:
      - REDIS_URL=redis://redis:6379
    volumes:
      - repos_data:/app/repos
      - chroma_data:/app/chroma_db
    depends_on: [redis, backend]

  celery_beat:
    build: ./backend
    command: celery -A app.tasks.celery_app beat --loglevel=info
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on: [redis]

  frontend:
    build: ./frontend
    ports: ["3000:3000"]
    environment:
      - NEXT_PUBLIC_API_URL=http://localhost:8000
    depends_on: [backend]

volumes:
  redis_data:
  chroma_data:
  repos_data:

docker-compose.prod.yml:
Same as above but:
- Remove volume mounts (code baked into image)
- Remove --reload from uvicorn
- Add restart: unless-stopped to all services
- Use .env.prod for environment
- Add nginx service for reverse proxy
- Workers: --concurrency=4
```

---

## PHASE 8 — Tests

---

### PROMPT 14 — Test suite

```
In backend/tests/, create a comprehensive test suite:

tests/test_rag.py:
- test_chunker_python: Parse a sample Python file, assert chunks have correct metadata
- test_chunker_fallback: Pass an unsupported file, assert sliding window fallback works
- test_hybrid_search_returns_results: Mock ChromaDB and BM25, assert hybrid search merges correctly
- test_reciprocal_rank_fusion: Unit test the RRF merge algorithm with known inputs
- test_redis_cache_hit: Mock Redis returning a cached embedding, assert embed API is NOT called

tests/test_api.py (using httpx.AsyncClient and pytest-asyncio):
- test_index_repo_queues_task: POST /repos/index returns task_id and status=queued
- test_index_repo_invalid_url: POST with non-GitHub URL returns 422
- test_get_status_not_found: GET /repos/unknown/status returns 404
- test_health_endpoint: GET /health returns 200 with redis and chroma status
- test_chat_requires_indexed_repo: POST /chat with unindexed repo returns 404

tests/test_agents.py:
- test_intent_router_qa: Query "where is auth?" routes to "qa"
- test_intent_router_readme: Query "generate readme" routes to "readme"
- test_intent_router_security: Query "find vulnerabilities" routes to "security"
- test_review_agent_adds_confidence: Mock crew output, assert confidence score present in result

conftest.py:
- Fixtures: async_client, mock_redis, mock_chromadb, sample_repo_id
- Use pytest-asyncio with asyncio_mode="auto"
- Set ENVIRONMENT=test to disable Sentry and use in-memory Redis

Add to pyproject.toml:
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]

[tool.coverage.run]
source = ["app"]
omit = ["tests/*"]
```

---

## PHASE 9 — CI/CD and Deployment

---

### PROMPT 15 — GitHub Actions CI pipeline

```
Create .github/workflows/ci.yml:

name: CI

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    services:
      redis:
        image: redis:7-alpine
        ports: ["6379:6379"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: pip
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest-cov
      - name: Run tests
        working-directory: backend
        env:
          REDIS_URL: redis://localhost:6379
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY_TEST }}
          ENVIRONMENT: test
        run: pytest tests/ --cov=app --cov-report=xml -v
      - uses: codecov/codecov-action@v4

  backend-lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install ruff mypy
      - run: ruff check backend/app/
      - run: mypy backend/app/ --ignore-missing-imports

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
        working-directory: frontend
      - run: npm run build
        working-directory: frontend
        env:
          NEXT_PUBLIC_API_URL: http://localhost:8000

  docker-build:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]
    steps:
      - uses: actions/checkout@v4
      - uses: docker/setup-buildx-action@v3
      - name: Build backend image
        uses: docker/build-push-action@v5
        with:
          context: ./backend
          push: false
          tags: code-assistant-backend:ci
      - name: Build frontend image
        uses: docker/build-push-action@v5
        with:
          context: ./frontend
          push: false
          tags: code-assistant-frontend:ci
```

---

### PROMPT 16 — Production deployment on Railway + Vercel

```
Create deployment configuration for Railway (backend) and Vercel (frontend).

1. Create backend/railway.toml:

[build]
builder = "DOCKERFILE"
dockerfilePath = "Dockerfile"

[deploy]
startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2"
healthcheckPath = "/health"
healthcheckTimeout = 30
restartPolicyType = "ON_FAILURE"
restartPolicyMaxRetries = 3

2. Create .github/workflows/deploy.yml:

name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    needs: [backend-test, frontend-test]  # from ci.yml
    steps:
      - uses: actions/checkout@v4
      - name: Install Railway CLI
        run: npm install -g @railway/cli
      - name: Deploy to Railway
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
        run: |
          cd backend
          railway up --service code-assistant-backend --detach

  deploy-frontend:
    runs-on: ubuntu-latest
    needs: deploy-backend
    steps:
      - uses: actions/checkout@v4
      - uses: amondnet/vercel-action@v25
        with:
          vercel-token: ${{ secrets.VERCEL_TOKEN }}
          vercel-org-id: ${{ secrets.VERCEL_ORG_ID }}
          vercel-project-id: ${{ secrets.VERCEL_PROJECT_ID }}
          working-directory: ./frontend
          vercel-args: '--prod'

3. Create backend/.env.example:
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://...
CHROMA_PERSIST_DIR=/app/chroma_db
REPOS_BASE_DIR=/app/repos
SENTRY_DSN=https://...
ENVIRONMENT=production
MAX_REPO_SIZE_MB=500
LOG_LEVEL=INFO

4. Create frontend/.env.example:
NEXT_PUBLIC_API_URL=https://your-backend.railway.app
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=pk_...
CLERK_SECRET_KEY=sk_...

5. Add to README.md a Deployment section:

## Deploying to Production

### Prerequisites
- Railway account + project created
- Vercel account + project created
- Redis instance (Railway addon or Upstash)
- GitHub repo with secrets set:
  RAILWAY_TOKEN, VERCEL_TOKEN, VERCEL_ORG_ID, VERCEL_PROJECT_ID,
  OPENAI_API_KEY_TEST (for CI), SENTRY_DSN

### Steps
1. Push to main branch
2. CI pipeline runs tests automatically
3. On success, backend deploys to Railway
4. Frontend deploys to Vercel pointing at the Railway URL

### Environment Variables on Railway
Set all variables from .env.example in Railway dashboard.
Railway provides Redis as an addon — copy the REDIS_URL it generates.

### Scaling
- Increase Railway worker count by changing --workers in startCommand
- Add a second Celery worker service in Railway for heavy indexing load
- ChromaDB: for production scale, switch to Chroma Cloud or Qdrant Cloud
```

---

### PROMPT 17 — Final wiring and README

```
Do a final integration pass across the entire project:

1. In backend/app/main.py, ensure:
   - On startup: verify Redis connection, log all loaded settings (without secret values)
   - On startup: create REPOS_BASE_DIR and CHROMA_PERSIST_DIR if they don't exist
   - Include proper OpenAPI tags for all route groups
   - Add rate limiting middleware: 60 requests/minute per IP using slowapi

2. In backend/app/dependencies.py, create reusable FastAPI dependencies:
   - get_settings() -> Settings
   - get_redis() -> RedisClient  
   - get_retriever(repo_id: str) -> HybridRetriever (validates repo is indexed)
   - verify_repo_indexed(repo_id: str, redis: RedisClient) — raises 404 if not

3. Add input validation throughout:
   - GitHub URL must match: https://github.com/{owner}/{repo}
   - repo_id must be alphanumeric + hyphens only
   - Questions max 500 characters
   - Reject repos over MAX_REPO_SIZE_MB

4. Add the following to the project root README.md:

# Code Intelligence Assistant
> AI-powered multi-agent system for understanding any GitHub codebase

## Features
- RAG-powered Q&A with file and line citations
- Automatic README generation
- Security vulnerability scanning
- Hybrid semantic + keyword search
- Redis-cached results for instant repeat queries

## Quick Start (Development)
git clone <this-repo>
cp backend/.env.example backend/.env  # fill in your keys
docker-compose up

Open http://localhost:3000

## Architecture
- Backend: FastAPI + CrewAI + LangGraph
- Vector DB: ChromaDB (persistent)
- Cache: Redis (3-tier TTL strategy)
- Frontend: Next.js 14

5. Verify all imports resolve correctly across all modules.
   Fix any circular imports by moving shared types to models/.
   
6. Add a scripts/seed_demo.py that:
   - Indexes a small public GitHub repo (e.g., https://github.com/tiangolo/fastapi)
   - Runs a test Q&A query
   - Generates a README
   - Prints results to console
   Use this to demo the system is working end-to-end.
```

---

## Build Order Summary

| Step | Prompt | What you get |
|---|---|---|
| 1 | PROMPT 1 | Full folder structure |
| 2 | PROMPT 2 | Config, logging, Redis client |
| 3 | PROMPT 3 | Repo cloning + Tree-sitter chunking |
| 4 | PROMPT 4 | ChromaDB + hybrid search |
| 5 | PROMPT 5 | Agent tools + LLM setup |
| 6 | PROMPT 6 | All 8 CrewAI agents |
| 7 | PROMPT 7 | 3 CrewAI crews |
| 8 | PROMPT 8 | LangGraph workflow |
| 9 | PROMPT 9 | FastAPI endpoints |
| 10 | PROMPT 10 | Celery background jobs |
| 11 | PROMPT 11 | Next.js setup + pages |
| 12 | PROMPT 12 | UI components |
| 13 | PROMPT 13 | Docker + Compose |
| 14 | PROMPT 14 | Test suite |
| 15 | PROMPT 15 | GitHub Actions CI |
| 16 | PROMPT 16 | Railway + Vercel deployment |
| 17 | PROMPT 17 | Final wiring + root README |

---

## Environment Variables Checklist

Before running, ensure these are set in backend/.env:

```
OPENAI_API_KEY=           # Required
ANTHROPIC_API_KEY=        # Optional (Claude fallback)
REDIS_URL=                # Required (redis://localhost:6379 for local)
CHROMA_PERSIST_DIR=./chroma_db
REPOS_BASE_DIR=./repos
SENTRY_DSN=               # Optional but recommended for production
ENVIRONMENT=development
MAX_REPO_SIZE_MB=500
EMBEDDING_MODEL=text-embedding-3-small
LLM_MODEL=gpt-4o
```

Frontend .env.local:
```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=    # From clerk.com
CLERK_SECRET_KEY=                     # From clerk.com
```

---

*Generated for hackathon use. Estimated build time with AI code editor: 8–12 hours.*
