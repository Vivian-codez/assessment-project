# Verism AI — Authoritative System & Codebase Audit Report

**Date:** November 21, 2026  
**Auditor:** Senior Full-Stack, DevOps & Systems Architect  
**Repository:** Verism AI (`Prototype`)  
**Live Frontend Reference:** [https://assessment-project-jycg.vercel.app/](https://assessment-project-jycg.vercel.app/)  
**Core Motto:** *"AI suggests. You stamp. Every grade waits for your approval."*

---

## 1. Executive Summary & System Health

Verism AI is an automated, teacher-centric assessment platform designed for rubric-based grading, exemplar solution benchmarking, peer-to-peer collision detection, and web plagiarism auditing. 

While core algorithms for FERPA encryption, vector similarity calculation, and Gemini 2.5 Flash evaluation are functional, the system has suffered from structural fragmentation across recent iterations. Specifically:
- **Database & Persistence:** The application silently falls back from PostgreSQL to a local SQLite database (`verism.db`) when connection errors or TCP socket restrictions occur. Database tables are created via ad-hoc SQLAlchemy `create_all()` and raw SQL `ALTER TABLE` loops on application startup instead of reproducible, declarative Alembic migrations.
- **Authentication & Security:** Authentication currently relies on bearer tokens stored in browser `localStorage`, lacking HTTP-only cookie support, rotating refresh tokens, session revocation deny-lists in Redis, and brute-force rate limiting.
- **Background Worker & Grading Pipeline:** Celery runs as a single monolithic worker pool (`concurrency=4`) without dedicated queues (`extract`, `ocr`, `grade`, `similarity`, `export`). Heavy file extraction or OCR tasks block real-time grading, creating severe pipeline bottlenecks.
- **Frontend & Dashboard Synchronization:** Discrepancies exist between student count aggregates on courses and live roll-call queries. Furthermore, a duplicate JSX tag block in `RosterView.tsx` breaks the Vite production build, and TypeScript strict linting flags multiple unvalidated `any` typings.

---

## 2. Inventory: What Works

| Capability | Module / File Path | Status | Verification Detail |
| :--- | :--- | :--- | :--- |
| **FERPA/GDPR Encryption & Pseudonymization** | `backend/app/core/security.py`<br>`backend/app/services/ferpa_service.py` | **Operational** | AES-256 (Fernet) encryption of student PII (Name, Roll, Email) at rest; regex scrubbing before sending prompts to Gemini. Verified by unit tests. |
| **Gemini 2.5 Flash Grading Engine** | `backend/app/services/gemini_service.py`<br>`backend/app/services/tenant_gemini_service.py` | **Operational** | Generates structured JSON responses conforming to `StructuredGradingOutput` schema with criteria breakdowns, scores, qualitative evidence, and AI-content probability. |
| **Vector Similarity & Collision Detection** | `backend/app/services/vector_service.py` | **Operational** | Document embedding generation (768-dim) and exact n-gram matching heuristics (`find_matching_phrases`, min 4 words). Qdrant vector database with in-memory fallback. |
| **Multi-Format Roster Ingestion Service** | `backend/app/services/roster_parser_service.py` | **Operational** | Delimiter-sniffed CSV/TSV, openpyxl for XLSX/XLS, pypdf for PDF, python-docx for DOCX, and Gemini multimodal vision fallback for scanned rosters. |
| **Interactive Header Course Switcher** | `frontend/src/routes/index.tsx` | **Operational** | Course and section switcher synced across views with dropdown selection and dynamic state updates. |

---

## 3. Inventory: What Is Mocked or Staged

| Component | File Path | Current Mock / Staged Implementation | Target Replacement |
| :--- | :--- | :--- | :--- |
| **Supabase PostgREST Layer** | `backend/app/core/supabase.py`<br>`backend/app/services/supabase_service.py` | Staged stub initialized with placeholder credentials. When `USE_SUPABASE=false`, returns empty stubs or redirects to local models. | Fully decouple and standardize all queries on native PostgreSQL via SQLAlchemy 2.x and Alembic. |
| **Qdrant Vector DB** | `backend/app/core/config.py`<br>`backend/app/services/vector_service.py` | Embedded `:memory:` fallback mode when network socket connection to `http://localhost:6333` fails. | Standardized Qdrant container with persistent volume and TCP retry handling. |
| **Web Plagiarism Scanning** | `backend/app/services/gemini_service.py`<br>`backend/app/models/submission.py` | `web_plagiarism_score` is populated via Gemini search heuristics or simulated web match payloads. | Direct web search citation extraction with grounded URL references. |
| **Instructor Session Storage** | `backend/app/models/user.py` (`UserSession`) | Model exists in schema but sessions are not revoked on logout, nor checked on token validation. | Redis-backed token deny-list + DB session table with absolute and idle timeouts. |

---

## 4. Inventory: What Is Broken (Root Causes & File Paths)

### 4.1 Database Architecture & Connection Severing
* **Symptom:** Backend silently reverts to SQLite `verism.db` upon initial connection failure, leading to split-brain persistence between Docker PostgreSQL and local files.
* **Root Cause:** In `backend/app/core/database.py` (lines 147–160), an unhandled exception during PostgreSQL `engine.connect()` logs a warning and creates an engine pointing to `sqlite:///verism.db`. In addition, SQLite `QueuePool` with thread concurrency triggers database locking deadlocks during concurrent requests.
* **File Path:** `backend/app/core/database.py` (lines 98–165).

### 4.2 Schema Incompleteness & Alembic Bypass
* **Symptom:** Running `alembic upgrade head` on a fresh PostgreSQL instance fails due to missing foundational tables (`users`, `classrooms`, `courses`, `assignments`).
* **Root Cause:** `backend/alembic/versions/` only contains `0001_multi_tenant_evaluation.py`, which adds `assignment_folders`, `monthly_usages`, and foreign keys referencing `users.id` and `submissions.id`. The base tables were created at runtime via `Base.metadata.create_all()` and manual `ALTER TABLE` loops inside FastAPI's `lifespan` in `backend/app/main.py` (lines 73–118).
* **File Path:** `backend/alembic/versions/0001_multi_tenant_evaluation.py`, `backend/app/main.py` (lines 53–126).

### 4.3 Multi-Tenant Isolation Discrepancy
* **Symptom:** Confusion between `User` and `Instructor` models. Some courses reference `instructor_id` pointing to `instructors`, while the user authentication pipeline issues tokens with `users.id`.
* **Root Cause:** Redundant dual models `User` (`backend/app/models/user.py`) and `Instructor` (`backend/app/models/instructor.py`). `auth.py` maintains an ad-hoc synchronization function `get_current_instructor` (lines 185–221) that mirrors `User` rows into `Instructor` rows upon request.
* **File Path:** `backend/app/models/course.py`, `backend/app/models/instructor.py`, `backend/app/models/classroom.py`, `backend/app/api/v1/auth.py`.

### 4.4 Authentication & Token Vulnerabilities
* **Symptom:** No refresh token rotation, no secure cookie handling, no token revocation on logout, and no rate limiting.
* **Root Cause:**
  1. `backend/app/api/v1/auth.py` only implements single-token JWT generation with 24-hour expiration (`ACCESS_TOKEN_EXPIRE_MINUTES = 1440`).
  2. Tokens are sent only in JSON responses and stored in browser `localStorage` (`frontend/src/lib/api.ts`, lines 135–150), leaving them vulnerable to XSS.
  3. No `/auth/refresh`, `/auth/forgot-password`, `/auth/reset-password`, or `/auth/change-password` endpoints exist.
  4. Missing Redis rate-limiter on `/auth/login` to thwart brute-force password guessing.
* **File Path:** `backend/app/api/v1/auth.py`, `frontend/src/lib/api.ts`.

### 4.5 Celery Queue Monolith & Slow Grading Pipeline
* **Symptom:** Bulk file uploads and grading jobs freeze the entire queue; concurrent users experience timeouts.
* **Root Cause:**
  1. Celery worker configuration in `backend/app/workers/celery_app.py` has no defined routing keys or separate queues.
  2. In `docker-compose.yml`, a single `celery_worker` container consumes all tasks.
  3. When large PDF parsing or OCR runs occur, CPU-bound tasks starve fast Gemini API dispatch tasks.
* **File Path:** `backend/app/workers/celery_app.py`, `backend/app/workers/evaluation_tasks.py`, `docker-compose.yml` (lines 81–108).

### 4.6 Frontend Build Failure & ESLint Errors
* **Symptom:** `npm run build` fails with `Expected corresponding JSX closing tag for 'div'` in `RosterView.tsx`. `npm run lint` fails with 62 errors on `@typescript-eslint/no-explicit-any`.
* **Root Cause:**
  1. In `frontend/src/components/RosterView.tsx` (lines 921–932), duplicate unclosed tags remained after a merge.
  2. Loose `any` typing across API handlers and UI views triggers strict ESLint rules.
* **File Path:** `frontend/src/components/RosterView.tsx` (lines 910–933), `frontend/src/lib/api.ts`, `frontend/src/routes/index.tsx`.

### 4.7 Docker Infrastructure Deficiencies
* **Symptom:** Frontend container runs `npm run dev` in development mode instead of an optimized production Nginx build; healthchecks on backend services lack dependent readiness.
* **Root Cause:** `frontend/Dockerfile` uses a single-stage node image running `npm run dev -- --host 0.0.0.0 --port 3000`. `docker-compose.yml` lacks segregated Celery workers (`worker-extract`, `worker-ocr`, `worker-grade`, `worker-similarity`, `worker-export`) and Celery beat.
* **File Path:** `frontend/Dockerfile`, `docker-compose.yml`.

---

## 5. Remediation Roadmap: Phase 1 & Phase 2

```mermaid
flowchart TD
    subgraph Phase 1: Infrastructure, Database & Auth
        A[Docker Infrastructure Hardening] --> B[SQLAlchemy 2.x Schema & Full Alembic Migration]
        B --> C[PostgreSQL Connection Pool & TCP Keep-Alives]
        C --> D[Multi-Tenant Auth Engine: Refresh Tokens, httpOnly Cookies, Redis Deny-List]
    end

    subgraph Phase 2: Courses, Roll Call & Multi-Format Ingestion
        D --> E[Course & Section Unified CRUD]
        E --> F[Universal Multi-Format Roster Ingestion Engine]
        F --> G[Interactive Roll Call Preview & Row-Level Validation]
        G --> H[Consistent Relational Count Computation across UI]
    end

    subgraph Verification & Gate
        H --> I[Automated Test Suite: Pytest, ESLint, Vite Build, Docker Health]
    end
```

### Execution Priority:
1. **Phase 1: Infrastructure, Database, Auth**
   - Author multi-stage `backend/Dockerfile` and production `frontend/Dockerfile` (Nginx on port 3000).
   - Author comprehensive `docker-compose.yml` with segregated Celery workers and healthcheck dependencies.
   - Unify database schema: Merge `Instructor` into `User` with organization/tenant scoping.
   - Author single authoritative Alembic migration initializing all tables.
   - Implement complete auth lifecycle: `/auth/register`, `/auth/login`, `/auth/logout`, `/auth/refresh`, `/auth/change-password`, `/auth/forgot-password`, `/auth/reset-password` with `httpOnly` secure cookies, rotating refresh tokens, and Redis deny-list.
2. **Phase 2: Courses, Roll Call, Students (Any File Format)**
   - Fix JSX syntax error in `frontend/src/components/RosterView.tsx`.
   - Implement universal document and roster parser handling CSV, TSV, XLSX, XLS, PDF, DOCX, TXT, and images.
   - Sync real relational enrollment counts across courses, dashboard cards, and roll call tables.
   - Guarantee zero mock data, zero hardcoded numbers, and line-by-line English code comments throughout.

