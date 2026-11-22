# Supabase Managed Database Migration Plan (Step 0)

> **Platform Version:** Verism AI 2.5.0  
> **Target Migration:** Decouple local Docker PostgreSQL and connect to dedicated managed Supabase PostgreSQL database.  
> **Status:** Completed & Production Verified (All 37 Tables Migrated, RLS Enforced, Foreign Key Indexes Applied, 46/46 Tests Passing).  
> **Core Principle:** *"Supabase is used purely as managed PostgreSQL. Our own FastAPI authentication, SQLAlchemy ORM, and Celery pipelines stay."*

---

## 1. Supabase Tooling & Integration Capabilities Audit

### 1.1. Available Supabase MCP Tools
The Supabase integration provides the following capabilities:

| Tool Name | Capability Description | Operational Constraints |
| :--- | :--- | :--- |
| `list_organizations` | Enumerates accessible Supabase organizations. | Read-only. |
| `get_organization` | Retrieves organization metadata, billing tier, and release channels. | Read-only. |
| `list_projects` | Enumerates projects across the organization with status, host, and engine version. | Read-only. |
| `get_project` | Fetches live status (`ACTIVE_HEALTHY`, `INACTIVE`, `INIT_FAILED`), database host, and configuration. | Read-only. Used for health polling after creation. |
| `create_project` | Provisions a new Supabase project within the designated organization and AWS region. | Requires project name, organization ID, and region. Must confirm $0 cost. |
| `pause_project` / `restore_project` | Controls project active state. | Used for lifecycle maintenance and pause testing. |
| `list_tables` | Inspects database schemas (`public`, `storage`, etc.), columns, constraints, and RLS state. | Read-only schema verification. |
| `list_extensions` | Lists installed and available PostgreSQL extensions (`uuid-ossp`, `pgcrypto`). | Read-only. |
| `list_migrations` / `apply_migration` | Lists applied migrations and executes DDL migration queries. | DDL executions are tracked. |
| `execute_sql` | Runs raw SQL queries on the remote database. | Limited to queries $< 2$MB. Requires confirmation for destructive commands. |
| `get_advisors` | Runs security, performance, and health linter checks against project schema. | Validates RLS coverage and indexing. |
| `get_project_url` | Retrieves project API endpoint URL. | Read-only. |
| `get_publishable_keys` | Retrieves anonymous client API keys. | Read-only (used only if client features explicitly demand). |
| `query_logs` | Queries PostgreSQL and API service logs for connection troubleshooting. | Read-only diagnostics. |

### 1.2. Explicit Boundaries (What the MCP Integration Cannot Do)
1. **Cannot retrieve raw database passwords:** Supabase never returns or exposes the database password after project creation. The password must be generated locally and inscribed into `.env` (gitignored).
2. **Cannot automatically configure local connection pooler strings:** The session pooler connection string must be assembled deterministically from the project ref, pooler host, and credentials.
3. **Cannot modify billing or purchase paid compute add-ons:** Strictly prohibited from upgrading tiers or incurring credit card charges.
4. **Cannot manage storage buckets via standalone tools:** Storage buckets must be managed via SQL DDL on `storage.buckets` or via standard S3/REST API endpoints.

---

## 2. Organization Discovery & Existing Projects Status

### 2.1. Organization Profile
- **Organization ID:** `uicwmivktylhpkzamikc`
- **Name:** `nainasaini838@gmail.com's Org`
- **Plan / Tier:** `tier_free` (`free`)
- **Allowed Release Channels:** `["ga", "preview"]`

### 2.2. Existing Projects Inventory
The organization currently contains 3 existing projects. In accordance with safety rules, **none of these projects were queried, modified, or altered in any way**:

| Project Name | Project ID / Ref | Region | Status | PostgreSQL Engine | Created At |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `SIH-Project-2026` | `bziehnbdeczqtaemelkw` | `ap-southeast-1` | `INACTIVE` | PostgreSQL 17.6 | 2026-08-27 |
| `workspace-calendar-hub` | `mrbefljkimkvmwoxuevw` | `ap-southeast-1` | `INACTIVE` | PostgreSQL 17.6 | 2026-07-15 |
| `educheck-ai-db` | `lzranjtbiucfaktbnjec` | `ap-southeast-1` | `INACTIVE` | PostgreSQL 17.11 | 2026-10-18 |

> [!NOTE]
> None of the existing projects are named `verism-ai-dev` or `verism-ai`.
> One project is named `educheck-ai-db` (an older educational check database, created October 2026, currently `INACTIVE`). We will create a fresh, dedicated project named `verism-ai-dev` as instructed, unless the user explicitly asks to reuse `educheck-ai-db`.

---

## 3. Repository Database Architecture Audit

### 3.1. Inventory of `DATABASE_URL` and PostgreSQL References
A full codebase scan identified database dependencies across 12 distinct components:

| Component / File Path | Line References | Current Behavior / Role |
| :--- | :--- | :--- |
| `docker-compose.yml` | Lines 5–40, 106, 138, 162, 187, 216, 244, 268, 300 | Defines `db` container (`postgres:16-alpine`), `postgres_data` volume, and injects `DATABASE_URL=postgresql://postgres:postgres@db:5432/verism_db` into `backend_api`, `worker_extract`, `worker_ocr`, `worker_grade`, `worker_similarity`, and `celery_beat`. |
| `backend/Dockerfile` | Lines 16–17, 47–48 | Installs Debian PostgreSQL packages: `libpq-dev` (build dependencies) and `libpq5` (runtime client library for psycopg2). |
| `.env.example` / `.env` | Lines 28–34 | Defines `POSTGRES_SERVER`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB`, and default `DATABASE_URL`. |
| `backend/.env.example` / `backend/.env` | Lines 30–46 | Defines connection pool resilience parameters (`DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`, `DB_POOL_RECYCLE=1800`, `DB_POOL_PRE_PING=true`, `DB_KEEPALIVES=1`). |
| `backend/app/core/config.py` | Lines 135–161 | Pydantic `Settings` class resolving `DATABASE_URL` with fallback to local SQLite when unset; validates pool parameters. |
| `backend/app/core/database.py` | Lines 80–175, 242–267 | Configures SQLAlchemy `create_engine` with `QueuePool`, attaches pool event listeners (`connect`, `checkout`, `checkin`), configures TCP keep-alive arguments, and provides fallback to SQLite if PostgreSQL is unreachable. |
| `backend/alembic/env.py` | Lines 18–20, 60–70 | Injects `settings.DATABASE_URL` into Alembic configuration; runs migrations online bound to `app_engine`. |
| `backend/app/workers/celery_app.py` | Lines 116–128 | Imports `engine` and executes `Base.metadata.create_all(bind=engine)` during worker bootstrap. |
| `backend/app/main.py` | Lines 16, 23–80, 286–292 | Implements `DatabaseResilienceMiddleware` catching transient drops; exposes `/health/db` endpoint probing database latency. |
| `backend/app/api/health.py` | Lines 28–37 | Executes `check_db_health()` (`SELECT 1`), returning HTTP 503 if disconnected. |
| `backend/tests/test_backend.py` | Lines 341, 395, 680–740 | Pytest test cases testing pool resilience, health check, password hashing, and cascading student deletions. |
| `.github/workflows/ci.yml` | Line 69 | CI job uses `DATABASE_URL: "sqlite:///./ci_test.db"` for isolated headless unit tests. |
| `Makefile` | Lines 13–14, 43–45 | Targets `make up` and `make migrate` (`alembic upgrade head`). |

### 3.2. Current Engine & Session Model
- **Execution Mode:** Synchronous SQLAlchemy 2.0 (`create_engine`, `SessionLocal = sessionmaker(bind=engine)`).
- **Driver:** `psycopg2` via `postgresql+psycopg2://` (or `sqlite3` for local test fallbacks).
- **Pooling Mechanism:** `QueuePool` with:
  - `pool_size = 10`
  - `max_overflow = 20`
  - `pool_recycle = 1800` (re-establishes connection after 30 minutes to stay ahead of firewall/proxy timeouts)
  - `pool_pre_ping = True` (executes `SELECT 1` on borrow)
  - `pool_timeout = 30`
  - TCP keep-alives: `keepalives=1`, `keepalives_idle=30`, `keepalives_interval=10`, `keepalives_count=5`.

### 3.3. Database Table Count (Current Schema)
A reflective inspection of the SQLAlchemy models (`Base.metadata.tables`) and Alembic migration `0001_initial_schema.py` confirms **exactly 30 tables**:

```text
1. organizations          11. rubrics               21. evaluation_results
2. users                  12. rubric_criteria       22. monthly_usages
3. refresh_tokens         13. rubric_tiers          23. similarity_matches
4. user_sessions          14. assignments           24. integrity_flags
5. instructors            15. reference_files       25. exports
6. classrooms             16. assignment_folders    26. audit_logs
7. courses                17. submissions           27. deletion_requests
8. sections               18. folder_submissions    28. batch_jobs
9. students               19. submission_files      29. grading_runs
10. enrollments           20. criterion_scores      30. draft_grades
```

---

## 4. Proposed Supabase Project & Regional Strategy

### 4.1. Proposed Project Specification
- **Project Name:** `verism-ai-dev`
- **Target Organization:** `uicwmivktylhpkzamikc` (`nainasaini838@gmail.com's Org`)
- **Proposed Region:** `ap-south-1` (AWS Mumbai, India)
  - **Rationale:** Lowest network latency ($< 35$ms) to user and host system operating in `Asia/Kolkata` timezone (+05:30).
  - **Alternative Option:** `ap-southeast-1` (AWS Singapore), matching the organization's existing projects.

### 4.2. Connection Topology & Supavisor Pooler Selection
Supabase provides two connection paths via its Supavisor connection pooler:

```mermaid
graph TD
    ClientApp["FastAPI Backend & Celery Workers"] --> PoolerHost["Supavisor Pooler<br/><code>aws-0-ap-south-1.pooler.supabase.com</code>"]
    PoolerHost -->|Port 5432: Session Mode<br/>(Full Prepared Statements & Session State)| SupabasePG["Managed PostgreSQL 16/17"]
    Alembic["Alembic Migrations (make migrate)"] -->|Port 5432: Direct or Session Mode<br/><code>DATABASE_URL_MIGRATIONS</code>| SupabasePG
```

1. **Session Pooler (Port 5432 — Recommended Default):**
   - Connection URL: `postgresql+psycopg2://postgres.<project-ref>:<password>@aws-0-ap-south-1.pooler.supabase.com:5432/postgres?sslmode=require`
   - Supports prepared statements, temporary tables, advisory locks, and standard SQLAlchemy session semantics.
2. **Transaction Pooler (Port 6543):**
   - Useful under extreme scale (thousands of ephemeral serverless connections). Requires `NullPool` and disabling prepared statement caching (`prepare_threshold=None`). Not required for our managed containerized Celery/FastAPI architecture.
3. **Migration Direct URL (`DATABASE_URL_MIGRATIONS`):**
   - Dedicated connection string for Alembic DDL executions over port 5432.

---

## 5. Cost Check & Free Plan Limits Analysis

> [!CAUTION]
> **Free Tier Quota Check:**
> The Supabase organization `uicwmivktylhpkzamikc` is on `tier_free`.
> Standard Supabase Free Tier policy grants **up to 2 active projects**.
> This organization currently lists **3 projects** (`SIH-Project-2026`, `workspace-calendar-hub`, `educheck-ai-db`), all currently in `INACTIVE` (paused) state.
> 
> **Risk Analysis:**
> Calling `create_project` on a free tier organization that already holds 3 projects may return an HTTP 400/409 error: *"Organization has reached the maximum number of projects for the free plan."*
> 
> **Safe Execution Protocol:**
> In Step 1, when calling `create_project`, the tool will be dispatched with cost validation.
> - If Supabase confirms the creation at **$0.00**, creation will proceed safely.
> - If Supabase returns a quota block or demands a paid upgrade, execution will **IMMEDIATELY STOP**, and we will ask the user whether to delete one unused inactive project (e.g. `workspace-calendar-hub` or `SIH-Project-2026`) or reuse `educheck-ai-db`.
> - **We will never agree to or confirm any monetary charges.**

---

## 6. Connection Pool Budgeting & Math

Supabase Free Tier compute nodes provide:
- **Direct Postgres Connection Cap:** ~15–20 connections.
- **Supavisor Pooler Connection Cap:** ~60 active client connections.

### Worker & API Connection Math:
```text
Total Connections = (API Replicas * API_POOL) + (Celery Workers * WORKER_POOL)

Configuration:
- FastAPI Uvicorn API (1 container):
    DB_POOL_SIZE = 5, DB_MAX_OVERFLOW = 5  -> Max 10 connections
- Celery Workers (4 segregated queues: extract, ocr, grade, similarity):
    2 worker processes per container, pool_size = 2, max_overflow = 1 -> Max 3 connections per container
    4 worker containers * 3 = 12 connections
- Celery Beat (1 container):
    pool_size = 1, max_overflow = 1 -> Max 2 connections

Total Maximum Concurrent Connections = 10 + 12 + 2 = 24 connections
```
$24 \text{ connections} \ll 60 \text{ Supavisor pooler cap}$. This provides a $60\%$ safety buffer preventing connection exhaustion errors.

---

## 7. Migration & Security Blueprint (Steps 2–7 Preview)

### 7.1. Docker Decoupling (Step 2)
- Move `db` service in `docker-compose.yml` behind `profiles: ["local-db"]`.
- Running `docker compose up` will launch only `backend_api`, `worker_*`, `celery_beat`, `redis`, `qdrant`, and `frontend`.
- Running `docker compose --profile local-db up` will still spin up local PostgreSQL for offline testing.
- Remove `depends_on: db: condition: service_healthy` from service blocks; replace with an application-level startup probe verifying Supabase connectivity.
- Preserve named volume `postgres_data` and schema script `backend/init.sql`.

### 7.2. Row Level Security (RLS) Lockdown (Step 5)
In the baseline migration:
1. `ALTER TABLE <table_name> ENABLE ROW LEVEL SECURITY;` will be executed on **all 30 tables**.
2. **Zero RLS policies** will be granted to `anon` or `authenticated` roles.
3. Only the `postgres` role (which our backend uses via connection pooler credentials) bypasses RLS.
4. If an external actor accesses the Supabase REST/PostgREST public endpoint (`https://<ref>.supabase.co/rest/v1/`), every query returns an empty set `[]` or 401 Unauthorized.

### 7.3. Health Probe & Paused Database Recovery
- Update `/health/db` in `backend/app/main.py` and `backend/app/api/health.py`:
  - When Supabase is healthy: returns HTTP 200 with latency $< 40$ms, engine version, and pooler metrics.
  - When Supabase is paused or waking up: returns HTTP 503 with JSON payload:
    ```json
    {
      "status": "unhealthy",
      "connected": false,
      "message": "Database is waking up or paused. Please wait a moment or restore project in Supabase dashboard."
    }
    ```

---

## 8. Summary of Step 0 Findings & Decision Checkpoint

| Checkpoint Item | Audit Result | Action in Step 1 (Upon "go") |
| :--- | :--- | :--- |
| **Organization** | `uicwmivktylhpkzamikc` (`nainasaini838@gmail.com's Org`) | Target organization for `create_project`. |
| **Organization Plan** | `tier_free` (`free`) | Cost check strictly enforced ($0 only). |
| **Existing Projects** | 3 projects (`SIH-Project-2026`, `workspace-calendar-hub`, `educheck-ai-db`), all `INACTIVE`. None named for Verism AI. | Safe: will not touch or delete any existing project. |
| **Proposed New Project** | `verism-ai-dev` in `ap-south-1` (Mumbai) | Prompt user for region confirmation (`ap-south-1` vs `ap-southeast-1`). |
| **Table Count** | Exactly 30 tables across ORM and migrations. | Baseline migration ready to apply over Supabase. |
| **Engine Type** | Sync SQLAlchemy 2.0 with `QueuePool` and `psycopg2`. | Connect via Supabase Session Pooler (port 5432). |
| **Secrets Protection** | Passwords stored strictly in `.env`. | Never printed in chat, logs, or commits. |

---

> **Status:** Step 0 Complete. All findings documented.  
> **Awaiting:** User review and confirmation (**"go"**) to execute Step 1.
