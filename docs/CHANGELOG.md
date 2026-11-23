# Verism AI — Version Release History & Changelog

> **Core Philosophy:** *"AI suggests. You stamp. Every grade waits for your approval. Grading never starts without your command."*  
> **Current Version:** 2.5.0 (Professional Single-Teacher SaaS Edition)

---

## Release Summary Overview

| Version | Release Phase | Focus Area | Key Deliverables |
| :--- | :--- | :--- | :--- |
| **v2.5.0** | Professional Polish & Supabase | Managed Cloud DB & UX Integrity | Supabase PostgreSQL (`uljtqfbkxsqzmboilwvw`, `aws-1-ap-south-1`), Decoupled Grading Start (`status="ready"`), Prompt-Fix Review Mode (`/api/v1/review-mode`), 360px-1920px responsive polish, Getting Started checklist, Help Drawer with hotkeys, zero-placeholder honest indicators. |
| **v2.4.0** | Phase 12 | System Documentation Suite | 17-document comprehensive architectural, API, and operational manual suite. |
| **v2.3.0** | Phase 11 | Automated Testing & CI | 35 Pytest suites passing (100%), GitHub Actions CI workflow. |
| **v2.2.0** | Phase 10 | Frontend Polish & Sellable Layer | Recharts analytics dashboard, Gradebook export menu, Trash Bin modal, Data privacy UI. |
| **v2.1.0** | Phase 9 | Data Governance & Retention | 30-day soft delete, Trash bin APIs, User data export ZIP, GDPR/DPDP endpoints, Security headers. |
| **v2.0.0** | Phase 8 | Spreadsheets & Gradebook Export | RFC-4180 CSV, CWE-1236 injection defense, UTF-8 BOM, openpyxl XLSX, Roll number regex ladder. |
| **v1.9.0** | Phase 7 | Real Analytics & Demo Data | Real SQL analytics, 60s Redis caching, 5-bucket histogram, skill gaps heatmap, sandbox seed. |
| **v1.8.0** | Phase 6 | Header Switcher & Global Context | Dynamic course & section dropdown switcher, cross-app state synchronization. |
| **v1.7.0** | Phase 5 | Roll Call & Roster Management | Student enrollment, CSV roster upload, classroom cohort linking. |
| **v1.6.0** | Phase 4 | Plagiarism & Integrity Engine | Winnowing AST fingerprinting, Jaccard shingling, AI writing indicator. |
| **v1.5.0** | Phase 3 | AI Grading & Pure Arithmetic | Gemini 2.5 Flash prompt engine, pure-Python deterministic marks aggregation. |
| **v1.2.0** | Phase 2 | Ingestion & Multi-Format Parsing | PDF, DOCX, ZIP, code AST extraction, SHA-256 deduplication. |
| **v1.0.0** | Phase 1 | Foundation & Database Reliability | Repo audit, PostgreSQL connection pooling resilience (`pool_pre_ping`, keepalives). |

---

## Detailed Chronological Changelog

### Version 2.5.0 — Professional UX Polish, Managed Supabase Database & Decoupled Grading
- **Supabase Cloud PostgreSQL Migration:** Connected backend to managed cloud PostgreSQL instance on Supabase (`uljtqfbkxsqzmboilwvw`, `ap-south-1` region) via QueuePool with `pool_recycle=1800` and `pool_pre_ping=True`. Docker Postgres container isolated under compose profile `local-db`.
- **Database RLS & Index Optimization:** Enabled Row Level Security (RLS) on all 37 database tables with covering foreign key indexes (0 Supabase advisor warnings). Added `grading_run_id` foreign key and index to `grade_history`.
- **Decoupled Grading Workflow:** Uploaded submissions transition to status `"ready"` (extracted and hash-checked) and never auto-grade. Teacher explicitly initiates grading via Start Grading panel with scope, filtering, and pre-flight estimation.
- **Prompt-Fix Review Mode (`/api/v1/review-mode`):** Added live prompt iteration endpoints: pre-flight checks, Start Grading orchestration, prompt versioning, structured feedback tags, Gemini-assisted prompt refinement, 3-sample dry runs with before/after diffs, and teacher grade override history.
- **Responsive Layout Stabilization (360px - 1920px):**
  - Eliminated horizontal header overflow at 360px viewport by constraining TopBar search and course selector widths.
  - Redesigned manual student enrollment modal for touch-friendly stacked inputs on mobile.
  - Added Help & Shortcuts slide-over drawer with hotkeys (`?`, `Esc`, `J/K`, `A`).
  - Added Getting Started 5-step onboarding checklist tracking real database progress.
- **Trust & Honesty Audit:** Removed unverified marketing claims; replaced with accurate technical disclaimers. Replaced fake placeholder percentages with real calculations or honest `"—"`. Added pluralization engine and detected CSV header reporting with sample template download.
- **Demo Data & Sandbox Tab Removal:** Removed the "Load Sandbox Demo Dataset" tab/button from the empty dashboard view, removed "Load Demo Data / Clear Demo Data" controls from the dashboard toolbar, and purged orphaned demo upload directories.

### Version 2.4.0 — Phase 12: Comprehensive Documentation Suite
- Published the authoritative 17-document technical and operational suite in `/docs/`:
  - `README.md`, `ARCHITECTURE.md`, `DATABASE.md`, `API.md`, `AUTH.md`, `INGESTION.md`, `GRADING.md`, `PLAGIARISM.md`, `CSV_EXPORT.md`, `DATA_DELETION_AND_PRIVACY.md`, `DASHBOARD_ANALYTICS.md`, `FRONTEND.md`, `DEPLOYMENT.md`, `TESTING.md`, `TROUBLESHOOTING.md`, `CHANGELOG.md`, `USER_MANUAL.md`.

### Version 2.3.0 — Phase 11: Automated Testing & Continuous Integration
- Implemented comprehensive automated test suite in `backend/tests/test_backend.py` achieving **35 passed tests with 100% pass rate**.
- Added `.github/workflows/ci.yml` providing automated linting, type-checking, backend pytest, and Vite build verification on every pull request.

### Version 2.2.0 — Phase 10: Sellable Frontend Layer & UI Polish
- Upgraded `Dashboard` view with real-time Recharts visualizations:
  - 4 KPI cards with trend badges vs. prior period.
  - Grade distribution 5-bucket histogram.
  - Longitudinal assignment trend line chart.
  - Rubric criterion skill gaps heatmap highlighting scores `< 70%` in warm clay.
  - 4-stage submission processing funnel.
  - Top & Needs-Attention student tables.
  - One-click sandbox demo data load/clear buttons.
- Enhanced `GradebookView` with 5-format export dropdown and high-confidence auto-approval switch.
- Added 30-Day Trash Bin recovery modal, GDPR data portability ZIP download, and legal policy viewer in `SettingsView`.
- Added global keyboard shortcut (`/`) for instant search bar activation.

### Version 2.1.0 — Phase 9: Data Governance, Soft Deletion & Security Headers
- Implemented 30-day soft deletion architecture using `deleted_at` timestamp.
- Added Trash Bin endpoints: `GET /api/v1/trash`, `POST /api/v1/trash/restore/{type}/{id}`, and `DELETE /api/v1/trash/permanent/{type}/{id}`.
- Added GDPR Article 20 / DPDP Section 12 Data Portability ZIP download (`GET /api/v1/user/export-all-data`).
- Implemented `SecurityHeadersMiddleware` enforcing HSTS, CSP, X-Frame-Options DENY, and nosniff.

### Version 2.0.0 — Phase 8: Gradebook Export & Spreadsheets Integration
- Implemented RFC-4180 CSV export with UTF-8 BOM (`\ufeff`) to ensure native Unicode rendering in Microsoft Excel.
- Implemented CWE-1236 Formula Injection defense prefixing hazardous characters (`=`, `+`, `-`, `@`, `\t`, `\r`) with single quotes.
- Added support for Google Classroom and Moodle offline grading worksheet formats.
- Implemented openpyxl XLSX generation with custom institutional navy styling and auto-fitting column widths.
- Built prioritized roll number regex waterfall ladder to accurately extract student identifiers from filenames.

### Version 1.9.0 — Phase 7: Real Analytics Engine & Redis Cache
- Replaced all dashboard mock values with live SQL aggregations in `backend/app/api/v1/reports.py`.
- Added 60-second Redis caching layer with automatic invalidation upon grade approvals.
- Implemented idempotent demo-data seed (`POST /api/v1/analytics/demo-data`) and teardown (`DELETE /api/v1/analytics/demo-data`).

### Version 1.5.0 — Phase 3: AI Auto-Grading & Pure Arithmetic
- Engineered structured Gemini 2.5 Flash prompt schema enforcing strict JSON responses.
- Implemented pure-Python marks aggregation engine to ensure 100% mathematical consistency and eliminate LLM arithmetic hallucinations.
- Enforced human teacher approval gate: all AI grades are staged as `draft_grades` until stamped by an educator.

### Version 1.0.0 — Phase 1: Database Connection Pooling Resilience
- Audited codebase and published initial findings in `/docs/AUDIT.md`.
- Stabilized SQLAlchemy connection pool with `pool_pre_ping=True`, `pool_recycle=1800`, and TCP keepalive parameters to permanently eliminate connection dropouts under cloud firewalls.
