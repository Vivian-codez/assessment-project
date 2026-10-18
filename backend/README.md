# Verism AI — Backend Service Architecture & Documentation

Verism AI is a production-grade, teacher-first backend service built to power AI-assisted grading, peer-to-peer plagiarism detection, and rubric management. It enforces the core educational principle: **"AI suggests, You stamp — every grade waits for teacher approval."**

---

## Architecture Overview

```
                                      ┌────────────────────────────────────────┐
                                      │   Next.js / Vite React Frontend        │
                                      │   (Teacher Console & Review Workspace) │
                                      └──────────────────┬─────────────────────┘
                                                         │
                                                  REST API (CORS)
                                                         │
                                                         ▼
┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                FastAPI Backend Service (Python 3.11+)                                 │
│                                                                                                       │
│   ├── app/api/v1/          - REST Routers (auth, courses, assignments, rubrics, grading, similarity)  │
│   ├── app/core/            - Pydantic v2 Config, DB Sessions, FERPA/GDPR Encryption                   │
│   ├── app/models/          - SQLAlchemy 2.0 ORM Models (encrypted PII, draft grades, similarity)     │
│   ├── app/schemas/         - Pydantic v2 Schemas with Gemini Structured JSON enforcement             │
│   ├── app/services/        - Gemini 2.5 Flash/Pro, Qdrant Vector Client, PDF Extractor, FERPA redactor│
│   └── app/workers/         - Celery Async Task Engine for 100+ batch submissions                     │
└──────────────┬───────────────────────────────┬───────────────────────────────┬────────────────────────┘
               │                               │                               │
               ▼                               ▼                               ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────┐
│    PostgreSQL Relational    │ │        Redis Broker         │ │    Qdrant Vector Database   │
│          Database           │ │     & Celery Workers        │ │  (Assignment Embeddings &   │
│  (Courses, Submissions,     │ │ (Async Evaluation Pipelines │ │  Peer-to-Peer Cross-Check)  │
│   Draft Grades, Audit Logs) │ │    for 100+ Submissions)    │ │                             │
└─────────────────────────────┘ └─────────────────────────────┘ └─────────────────────────────┘
                                               │
                                               ▼
                                ┌─────────────────────────────┐
                                │       Google GenAI Core     │
                                │   (Gemini 2.5 Flash / Pro)  │
                                │  - Multimodal PDF analysis  │
                                │  - Context Caching          │
                                │  - Structured JSON Schemas  │
                                └─────────────────────────────┘
```

---

## Key Capabilities & Implementation Highlights

### 1. FERPA & GDPR Privacy & Cryptography Handlers
- **Encrypted at Rest:** Student personally identifiable information (`student_name`, `student_roll`, `student_email`) is encrypted using Fernet (AES-128 in CBC mode with HMAC-SHA256 authentication).
- **Data Minimization & Pseudonymization:** Before any submission content is transmitted to Gemini LLMs, the student's name, email, and roll number are scrubbed and replaced with a deterministic pseudonym token (e.g. `STUDENT_A3F89B`). Linkage is securely re-established inside the backend before persisting draft grades.
- **Audit Logging:** Every grade approval, score edit, flag dismissal, and decrypt event is immutably logged in the `audit_logs` table.

### 2. Google GenAI Core (Gemini 2.5 Flash / Pro)
- **Structured JSON Schema Enforcement:** Generates strict JSON conforming to `StructuredGradingOutput`, returning individual criterion marks, rationales, overall scores, and AI content probabilities.
- **Context Caching:** Long rubrics and syllabi are cached via `client.caches.create` with a 2-hour TTL to reduce latency and API costs across 100+ batch submissions.
- **Multimodal PDF Processing:** Accepts native PDF bytes via `types.Part.from_bytes` or extracted text.

### 3. Qdrant Vector Plagiarism Engine
- Stores 768-dimensional dense embeddings for all assignment submissions.
- Executes cross-submission peer-to-peer similarity checks within each assignment batch.
- Automatically flags pairs exceeding the teacher's threshold (e.g., 90%+ similarity) and extracts verbatim matching phrases for side-by-side inspection.

### 4. Celery + Redis Async Batch Processing
- Asynchronously processes batches of 100+ student submissions without HTTP gateway timeouts.
- Emits real-time progress updates (0-100%) polled via `GET /api/v1/jobs/{job_id}`.

---

## Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── api_router.py      # Aggregates all v1 sub-routers
│   │       ├── auth.py            # Instructor profile & preferences
│   │       ├── courses.py         # Courses & real-time counts
│   │       ├── assignments.py     # Course assignments
│   │       ├── rubrics.py         # Rubric & criteria creation
│   │       ├── submissions.py     # Batch file upload (PDF/ZIP)
│   │       ├── grading.py         # Review queue & grade stamp/edit
│   │       ├── similarity.py      # Flagged pairs & comparison
│   │       ├── jobs.py            # Async batch evaluation triggers & polling
│   │       ├── gradebook.py       # Live gradebook spreadsheet matrix
│   │       ├── reports.py         # Course analytics & trends
│   │       └── audit.py           # FERPA/GDPR compliance logs
│   ├── core/
│   │   ├── config.py              # Pydantic Settings v2 configuration
│   │   ├── database.py            # SQLAlchemy 2.0 engine & session
│   │   ├── security.py            # FERPA AES encryption, JWT, password hashing
│   │   └── logging.py             # Structured audit logger
│   ├── models/                    # SQLAlchemy database entities
│   │   ├── instructor.py
│   │   ├── course.py
│   │   ├── assignment.py
│   │   ├── rubric.py
│   │   ├── submission.py          # Encrypted student fields
│   │   ├── draft_grade.py
│   │   ├── similarity_match.py
│   │   ├── batch_job.py
│   │   └── audit_log.py
│   ├── schemas/                   # Pydantic v2 schemas
│   ├── services/
│   │   ├── gemini_service.py      # Google GenAI SDK (Gemini 2.5 Flash/Pro)
│   │   ├── vector_service.py      # Qdrant client & peer similarity
│   │   ├── pdf_service.py         # PDF & document text extraction
│   │   └── ferpa_service.py       # PII anonymization & pseudonymization
│   ├── workers/
│   │   ├── celery_app.py          # Celery configuration
│   │   └── evaluation_tasks.py    # Background batch evaluation tasks
│   └── main.py                    # FastAPI application & CORS
├── scripts/
│   ├── init_db.py                 # Table initialization
│   └── seed_data.py               # Seed data matching frontend
├── tests/
│   └── test_backend.py            # Pytest test suite
├── Dockerfile                     # Python 3.11 container definition
├── docker-compose.yml             # Orchestration for API, Celery, Postgres, Redis, Qdrant
├── requirements.txt
├── pyproject.toml
└── .env.example
```

---

## Quick Start Guide

### Option 1: Docker Compose (Recommended for Full Stack)

Run the full stack (FastAPI, Celery worker, PostgreSQL, Redis, Qdrant) with one command:

```bash
# In the project root or /backend directory
docker compose up --build
```

The services will start at:
- **FastAPI API & Docs:** `http://localhost:8000/docs`
- **PostgreSQL:** `localhost:5432`
- **Redis:** `localhost:6379`
- **Qdrant Vector DB:** `http://localhost:6333/dashboard`

Seed initial data inside the container:
```bash
docker compose exec backend_api python scripts/seed_data.py
```

---

### Option 2: Local Development (Without Docker)

1. **Activate Virtual Environment:**
   ```powershell
   cd backend
   .\.venv\Scripts\Activate.ps1
   ```

2. **Initialize Database & Seed Data:**
   ```powershell
   python scripts/init_db.py
   python scripts/seed_data.py
   ```

3. **Start FastAPI Development Server:**
   ```powershell
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

4. **Run Background Celery Worker (Optional):**
   ```powershell
   celery -A app.workers.celery_app.celery_app worker --loglevel=info
   ```
   *(Note: If Celery/Redis is not running locally, the backend automatically executes batch jobs via FastAPI background tasks).*

5. **Run Sanity Tests:**
   ```powershell
   pytest
   ```

---

## Environment Variables (`.env`)

| Variable | Description | Default |
|---|---|---|
| `DATABASE_URL` | PostgreSQL or SQLite connection string | `postgresql://postgres:postgres@db:5432/verism_db` |
| `REDIS_URL` | Redis connection URL for broker & cache | `redis://redis:6379/0` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://redis:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result store | `redis://redis:6379/0` |
| `QDRANT_URL` | Qdrant vector database URL | `http://qdrant:6333` |
| `GEMINI_API_KEY` | Google AI Studio API Key for Gemini 2.5 | `(Optional - has intelligent fallback)` |
| `GEMINI_MODEL` | Gemini evaluation model | `gemini-2.5-flash` |
| `FERPA_ENCRYPTION_KEY` | 32-byte URL-safe base64 Fernet encryption key | `(Auto-generated)` |
| `BACKEND_CORS_ORIGINS` | Allowed frontend origins (JSON array) | `["http://localhost:3000","http://localhost:5173"]` |
