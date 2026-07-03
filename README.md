# StudyRAG

StudyRAG is being built phase by phase from the supplied build specification.

## Phase 1: Standalone RAG Core

This repo currently contains a testable Python RAG core before any FastAPI or
frontend code. The core covers:

- Text extraction interfaces for TXT, with optional PDF/DOCX adapters.
- Semantic-aware chunking with token windows, overlap, page metadata, and
  best-effort section heading detection.
- A local deterministic hashing embedding model for zero-cost development.
- An optional `sentence-transformers` embedding adapter for later local model
  use.
- Course-scoped hybrid retrieval using vector similarity plus BM25 keyword
  ranking combined with reciprocal rank fusion.
- Confidence-gated refusal before generation.
- Strict prompt construction with citation source tags and prompt-injection
  guardrails.
- Structured citation mapping from `[source N]` tags back to chunks.
- Conversation-history trimming by token budget so long chats degrade
  predictably.

Run the current verification suite:

```powershell
python -m unittest discover -s tests
```

The tests are written with `unittest` so they run without installing anything,
and they are also compatible with pytest collection.

## Phase 2: Persistence Layer

The repo now includes a Postgres persistence layer that wraps the Phase 1 core
without reimplementing chunking, embedding, retrieval scoring, refusal logic, or
prompt construction.

- `docker-compose.yml` starts Postgres with pgvector on local port `55433` and
  creates a `studyrag_test` database for integration tests.
- `src/studyrag_persistence` defines SQLAlchemy models for users, courses,
  documents, chunks, conversations, messages, and message citations.
- `documents.storage_url` is included so uploaded originals can later be opened
  from citations.
- `chunks.embedding_model` records which model produced each vector.
- `chunks.content_tsv` is a generated Postgres `tsvector` column for keyword
  retrieval.
- `migrations/versions/20260702_0001_initial_schema.py` creates the full schema,
  pgvector extension, GIN index for `content_tsv`, and HNSW cosine index for
  embeddings.
- `persist_document_chunks()` calls `studyrag_core.SemanticChunker` and the
  configured embedding model, then stores the resulting chunk rows.
- `PostgresHybridRetriever` exposes the same `retrieve(course_id, query, top_k)`
  shape as the in-memory retriever, but queries pgvector and full-text search in
  Postgres before combining ranks with reciprocal rank fusion.

Install database dependencies when you are ready to run Phase 2 against
Postgres:

```powershell
python -m pip install -e ".[db,test]"
docker compose up -d postgres
$env:DATABASE_URL="postgresql+psycopg://studyrag:studyrag@localhost:55433/studyrag"
python -m alembic upgrade head
```

Run the real Postgres integration test:

```powershell
$env:STUDYRAG_TEST_DATABASE_URL="postgresql+psycopg://studyrag:studyrag@localhost:55433/studyrag_test"
python -m unittest tests.test_postgres_persistence
```

The integration test performs a chunk -> embed -> store -> retrieve round trip
and asserts that retrieval remains course-scoped at the database query level.

## Phase 3: Object Storage And Ingestion

Phase 3 adds the upload and ingestion path while still writing through the Phase
2 persistence service:

- `src/studyrag_ingestion` contains the object storage abstraction and ingestion
  pipeline.
- `LocalObjectStorage` is used for development/tests.
- `S3CompatibleObjectStorage` supports S3-compatible storage, including
  Cloudflare R2, via `boto3`.
- Uploaded originals are stored first, and the resulting URL is written to
  `documents.storage_url`.
- `ingest_document_file()` extracts text with the existing
  `studyrag_core.extract_pages()`, then calls `persist_document_chunks()` so the
  chunk -> embed -> persist behavior remains shared.
- `src/studyrag_api` exposes only the Phase 3 ingestion endpoints:
  `POST /courses/{course_id}/documents` and `GET /documents/{document_id}/status`.
- Upload ingestion uses FastAPI `BackgroundTasks`. The code marks the exact swap
  point for replacing it with Redis + RQ if real document uploads start timing
  out.
- `documents.status` transitions through `pending`, `chunked`, `embedded`, or
  `failed`; corrupt files are caught and persisted as `failed`.

Install Phase 3 dependencies:

```powershell
python -m pip install -e ".[db,test,ingestion,api]"
```

Storage configuration:

```powershell
$env:STUDYRAG_STORAGE_BACKEND="local"
$env:STUDYRAG_LOCAL_STORAGE_DIR=".studyrag_storage"
```

For Cloudflare R2/S3:

```powershell
$env:STUDYRAG_STORAGE_BACKEND="r2"
$env:S3_BUCKET="your-bucket"
$env:S3_REGION="auto"
$env:S3_ENDPOINT_URL="https://<account-id>.r2.cloudflarestorage.com"
$env:S3_ACCESS_KEY_ID="..."
$env:S3_SECRET_ACCESS_KEY="..."
$env:S3_PUBLIC_BASE_URL="https://your-public-file-base-url"
```

Run Phase 3's real Postgres ingestion tests:

```powershell
docker compose up -d postgres
$env:STUDYRAG_TEST_DATABASE_URL="postgresql+psycopg://studyrag:studyrag@localhost:55433/studyrag_test"
python -m unittest discover -s tests
```

The ingestion tests upload a generated PDF through FastAPI into real
Postgres/pgvector, verify chunks and retrieval, and confirm a corrupt PDF ends
with `status=failed` without crashing the request.

## Phase 4: FastAPI Application Layer

Phase 4 extends `src/studyrag_api` into the authenticated application API:

- JWT auth with passlib password hashing:
  - `POST /auth/register`
  - `POST /auth/login`
- Authenticated, user-scoped courses:
  - `POST /courses`
  - `GET /courses`
  - `GET /courses/{id}`
- The Phase 3 document endpoints are now protected by the same bearer token and
  enforce course/document ownership:
  - `POST /courses/{id}/documents`
  - `GET /documents/{id}/status`
- Authenticated conversations:
  - `POST /courses/{id}/conversations`
  - `GET /conversations/{id}/messages`
- Streaming Q&A:
  - `POST /conversations/{id}/messages`
  - Returns `text/event-stream` token events followed by a final event with
    `{citations[], confidence, refused}`.
  - Uses `PostgresHybridRetriever` plus `StudyRAGCore`, so retrieval,
    confidence-gated refusal, prompt construction, and citation mapping remain
    centralized in the already-tested core/persistence layers.
  - Persists user/assistant messages and `message_citations`.
  - Applies `slowapi` rate limiting on the message endpoint.

Run the Phase 4 suite against real Postgres/pgvector:

```powershell
docker compose up -d postgres
$env:STUDYRAG_TEST_DATABASE_URL="postgresql+psycopg://studyrag:studyrag@localhost:55433/studyrag_test"
python -m unittest discover -s tests
```

The Phase 4 tests cover:

- register -> login -> create course -> upload PDF -> create conversation ->
  stream answer -> persist citations
- API-level user isolation, confirming User A cannot read User B's course or
  conversation
- refusal through the full HTTP stack when confidence is below threshold

Current full test count: 15 real tests against Postgres/pgvector.

## Phase 5: Evaluation Harness

Phase 5 adds a standalone evaluation harness under `eval/`:

- `eval/course_material.py` seeds a small course with multi-topic study notes.
- `eval/golden_dataset.json` contains 26 handwritten question/reference pairs:
  22 answerable questions and 4 expected refusals.
- `eval/runner.py` runs independently of the API against Postgres/pgvector,
  using `PostgresHybridRetriever` and `StudyRAGCore` directly.
- Results are written to:
  - `eval/results/latest.json`
  - `eval/results/latest.md`

Run the eval:

```powershell
docker compose up -d postgres
$env:STUDYRAG_TEST_DATABASE_URL="postgresql+psycopg://studyrag:studyrag@localhost:55433/studyrag_test"
python -m eval.runner --confidence-threshold 0.2
```

Latest retrieval results, generated with Ragas 0.4.3 ID-based context metrics
after the Phase 5.5b synthesis validation pass:

| Metric | Value |
|---|---:|
| Total examples | 32 |
| Context precision | 0.390 |
| Context recall | 1.000 |
| Refusal precision | 1.000 |
| Refusal recall | 1.000 |

Notes:

- Context precision/recall use Ragas ID-based metrics against expected chunk IDs.
- Faithfulness and answer relevancy are deterministic local proxies because no
  evaluator LLM API key is configured. They are useful development checks but
  should not be used as public Ragas scores or resume metrics yet.
- Phase 5.5 initially showed `top_k=1` could reach `1.000` precision/recall on
  the original 26-question set, but Phase 5.5b added synthesis questions and
  exposed that as overfit.
- Current default retrieval is `top_k=4`: precision is lower at `0.390`, but
  recall remains `1.000` on the expanded 32-question set, including multi-chunk
  synthesis questions.
- The before/after comparisons are in `eval/results/retrieval_precision_pass.md`
  and `eval/results/retrieval_synthesis_validation.md`.

## Phase 6: Frontend

Phase 6 adds a React + TypeScript + Vite client under `client/`:

- `LoginPage`, `CoursesPage`, `CourseDetailPage`, and `ChatPage`.
- Typed API client in `client/src/api/client.ts`.
- Streaming SSE token rendering in chat.
- Expandable citation chips with excerpts, document names, pages, source links,
  and wrapping behavior for the current `top_k=4` default.
- Confidence/refusal badges for low-support answers.
- A demo login button that calls `POST /auth/demo` when deployment demo mode is
  enabled.

Run the frontend checks:

```powershell
cd client
npm install
npm test
npm run build
```

## Phase 7: Deployment

The deployment split is:

- Backend API: Docker image from the repo root `Dockerfile`.
- Database: managed Postgres with the `vector` extension available.
- Frontend: Vercel deployment from `client/`, pointed at the deployed backend
  with `VITE_API_BASE_URL`.

`render.yaml` is included for a Render Blueprint backend deployment. The
frontend is intentionally not bundled into the backend image because Vercel is
the target client host.

Backend startup uses `python -m studyrag_deploy.runtime`, which runs:

1. `alembic upgrade head`, unless `STUDYRAG_SKIP_MIGRATIONS=true`.
2. Optional sample-course seeding when
   `STUDYRAG_SEED_SAMPLE_COURSE_ON_STARTUP=true`.
3. Uvicorn on `PORT`.

Deployment env checklist:

```text
DATABASE_URL
JWT_SECRET
STUDYRAG_CORS_ORIGINS=https://your-vercel-app.vercel.app
STUDYRAG_RETRIEVAL_TOP_K=4
STUDYRAG_MESSAGE_RATE_LIMIT=30/minute
STUDYRAG_STORAGE_BACKEND=r2
S3_BUCKET
S3_REGION
S3_ENDPOINT_URL
S3_ACCESS_KEY_ID
S3_SECRET_ACCESS_KEY
S3_PUBLIC_BASE_URL
LLM_API_KEY
LLM_MODEL
LLM_BASE_URL
RAGAS_EVALUATOR_API_KEY
RAGAS_EVALUATOR_MODEL
RAGAS_EVALUATOR_BASE_URL
RAGAS_EVALUATOR_EMBEDDING_MODEL
STUDYRAG_DEMO_ENABLED=true
STUDYRAG_SEED_SAMPLE_COURSE_ON_STARTUP=true
STUDYRAG_ATTACH_SAMPLE_COURSE_ON_REGISTER=true
```

`LLM_API_KEY`/`LLM_MODEL` enable OpenAI-compatible answer generation. If they
are unset, the API uses the deterministic extractive generator used by the test
suite.

`RAGAS_EVALUATOR_API_KEY`/`RAGAS_EVALUATOR_MODEL` enable real Ragas
LLM-as-judge faithfulness and answer-relevancy metrics. If they are unset,
`eval/runner.py` keeps those two metrics labeled as local deterministic
proxies. Context precision/recall remain ID-based metrics.

The deployed demo path is:

- `STUDYRAG_DEMO_ENABLED=true` exposes `POST /auth/demo`.
- `STUDYRAG_SEED_SAMPLE_COURSE_ON_STARTUP=true` seeds `StudyRAG Sample Course`
  from the curated eval material.
- `STUDYRAG_ATTACH_SAMPLE_COURSE_ON_REGISTER=true` also attaches the sample
  material to newly registered users, so the full register -> login -> ask
  smoke path works without requiring uploads.

Before sharing a public URL, verify:

```powershell
$env:STUDYRAG_TEST_DATABASE_URL="postgresql+psycopg://studyrag:studyrag@localhost:55433/studyrag_test"
python -m pytest

cd client
npm test
npm run build
```
