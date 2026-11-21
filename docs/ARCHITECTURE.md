# System Architecture & Technical Design

## 1. High-Level Architecture Overview

Verism AI is architected as a high-throughput, asynchronous, multi-tenant SaaS application designed to process thousands of student submissions concurrently while maintaining strict data isolation, cryptographic privacy, and sub-second UI responsiveness.

```mermaid
flowchart TD
    Client["Educator Browser / React 19 Frontend\n(Vite + TanStack Start SSR)"]
    Nginx["Nginx Reverse Proxy / Cloudflare Edge"]
    FastAPI["FastAPI 0.115+ Application Server\n(Uvicorn Asynchronous Workers)"]
    Postgres[("PostgreSQL 16 Relational Database\n(SQLAlchemy 2.x ORM + Alembic)")]
    Redis[("Redis 7 In-Memory Cache & Broker")]
    CeleryWorkers["Celery Distributed Workers\n(Ingestion, AST Parsing, Gemini Evaluation)"]
    GeminiAPI["Google Gemini 2.5 Flash API\n(google-genai Python SDK)"]
    Storage[("Encrypted Local/Cloud Storage\n(AES-256 Field Level Encryption)")]

    Client -->|HTTPS / WSS / REST| Nginx
    Nginx -->|Reverse Proxy / Load Balance| FastAPI
    FastAPI -->|Async Connection Pool / QueuePool| Postgres
    FastAPI -->|Token Cache / Rate Limiting / 60s Analytics| Redis
    FastAPI -->|Enqueue Batch Evaluation Jobs| Redis
    Redis -->|Dispatch Jobs| CeleryWorkers
    CeleryWorkers -->|Read/Write State| Postgres
    CeleryWorkers -->|Pseudonymized Prompts| GeminiAPI
    CeleryWorkers -->|Persist Submissions & Exports| Storage
```

---

## 2. Core Service Topology

### 2.1 Web & Application Layer
- **Framework:** FastAPI on Python 3.11+.
- **ASGI Server:** Uvicorn with asynchronous event loops (`asyncio` / `anyio`).
- **Connection Resilience:** SQLAlchemy `QueuePool` with:
  - `pool_pre_ping=True`: Test-on-borrow socket health check (`SELECT 1`).
  - `pool_recycle=1800`: 30-minute idle connection recycling to survive cloud firewall drops.
  - TCP Keep-Alives: `keepalives=1`, `keepalives_idle=30`, `keepalives_interval=10`, `keepalives_count=5`.
  - Resilience Decorator: `@with_db_retry(max_retries=3, backoff_base=0.5)` catching transient disconnects.
- **Enterprise Security Middleware:** Automatically injects:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `X-XSS-Protection: 1; mode=block`
  - `Strict-Transport-Security: max-age=31536000; includeSubDomains`
  - `Referrer-Policy: strict-origin-when-cross-origin`

### 2.2 Asynchronous Background Workers
- **Queue Broker:** Redis 7 with database slot 0 for Celery, slot 1 for 60s analytics caching, slot 2 for session token invalidation.
- **Worker Execution:** Celery 5.4+ with concurrency workers and prefetch multipliers tuned for I/O bound Gemini network calls.
- **Task Types:**
  - `process_submission_file`: Multi-format parsing (PDF, DOCX, ZIP, Code AST).
  - `evaluate_submission_batch`: Asynchronous grading orchestration with Gemini 2.5 Flash.
  - `run_pairwise_winnowing`: Cross-submission AST and n-gram similarity comparison.
  - `generate_bulk_gradebook_export`: Offline generation of comprehensive Excel workbooks and audit archives.

### 2.3 Client-Side Architecture
- **Framework:** React 19 + TypeScript.
- **Build System:** Vite 8 + TanStack Start (SSR + Nitro Cloudflare compatibility).
- **Navigation & Routing:** `@tanstack/react-router` with type-safe file routes.
- **State & Remote Synchronization:** `@tanstack/react-query` with optimistic cache updates and debounced mutation refetches.
- **Data Visualizations:** Recharts 2.15 for SVG-native interactive histograms, longitudinal trend lines, and skill-gap heatmaps.

---

## 3. Asynchronous Evaluation Workflow

```mermaid
sequenceDiagram
    autonumber
    actor Teacher as Educator
    participant UI as React Frontend
    participant API as FastAPI Backend
    participant Worker as Celery Worker
    participant Gemini as Google Gemini API
    participant DB as PostgreSQL

    Teacher->>UI: Uploads Submissions ZIP / PDF / Code
    UI->>API: POST /api/v1/assignments/{id}/submissions
    API->>DB: Persist Submissions (status: unprocessed)
    API->>Worker: Enqueue Batch Job (job_id)
    API-->>UI: 202 Accepted (job_id returned)
    
    par Background Evaluation
        Worker->>DB: Fetch Assignment, Rubric & Reference Solution
        Worker->>Worker: Extract Text / Code AST / Winnowing Fingerprints
        Worker->>Worker: Pseudonymize Student Identifiers (STUDENT_XYZ)
        Worker->>Gemini: POST generate_content (Structured JSON Schema)
        Gemini-->>Worker: Criterion Scores & Explanations JSON
        Worker->>Worker: Pure-Python Arithmetic Summation & Clamping
        Worker->>DB: Save DraftGrade (status: graded, is_stamped: false)
    end

    loop Poll Progress
        UI->>API: GET /api/v1/jobs/{job_id}
        API-->>UI: { status: "processing", progress: 75% }
    end

    UI->>Teacher: Toast: "Grading Complete! Ready for review."
    Teacher->>UI: Inspects AI Draft & Clicks "Approve Grade"
    UI->>API: POST /api/v1/grading/stamp/{id}
    API->>DB: Set Submission.status = "approved"
    API->>DB: Log Immutable FERPA AuditLog Record
    API-->>UI: 200 OK (Grade finalized)
```
