# Verism AI — Engineering & System Documentation Hub

> **Core Philosophy:** *"AI suggests. You stamp. Every grade waits for your approval."*  
> **Platform Version:** 2.4.0 (Enterprise SaaS Edition)  
> **Target Audience:** Educators, Academic Administrators, DevOps Engineers, and Security Auditors.

---

## 1. Documentation Catalog

Welcome to the comprehensive technical documentation suite for **Verism AI**, the teacher-first rubric auto-grading, benchmark evaluation, and academic integrity SaaS platform.

| Document | Purpose | Key Topics Covered |
| :--- | :--- | :--- |
| [**Architecture**](file:///docs/ARCHITECTURE.md) | High-Level Systems Overview | Microservices, FastAPI, Celery, Redis, Vite, Cloudflare Nitro, Mermaid Diagrams |
| [**Database**](file:///docs/DATABASE.md) | PostgreSQL & ORM Specifications | SQLAlchemy 2.x, PostgreSQL Schema, Foreign Keys, Indexing, Soft-Deletion, DDL Migrations |
| [**REST API Reference**](file:///docs/API.md) | Comprehensive API Catalog | OpenAPI v3, Request/Response Payloads, Authentication Headers, Error Handling |
| [**Authentication & Security**](file:///docs/AUTH.md) | Identity & Tenant Isolation | JWT Access/Refresh Rotation, HttpOnly Cookies, CSRF Defense, AES-256 Field Encryption |
| [**Document Ingestion**](file:///docs/INGESTION.md) | File Parsing & OCR Pipeline | Multi-format PDF, DOCX, ZIP, Code AST Extraction, Deterministic File Hash Caching |
| [**AI Auto-Grading**](file:///docs/GRADING.md) | Evaluation Pipeline & Benchmarking | Structured JSON Prompts, Pure-Python Exact Arithmetic, Spot-Check Calibration |
| [**Plagiarism & Integrity**](file:///docs/PLAGIARISM.md) | 3-Way Collision Detection | Winnowing AST Fingerprinting, Jaccard Shingling, AI Writing Indicators, Web Disclaimers |
| [**Gradebook & CSV Export**](file:///docs/CSV_EXPORT.md) | Spreadsheets & LMS Integrations | RFC-4180 CSV, CWE-1236 Injection Defense, UTF-8 BOM, Google Classroom & Moodle Formats |
| [**Privacy & Data Governance**](file:///docs/DATA_DELETION_AND_PRIVACY.md) | Compliance & Retention | 30-Day Trash Bin, Permanent Cascade Purge, GDPR Art. 17/20, DPDP Sec. 12, ZIP Export |
| [**Analytics & Dashboard**](file:///docs/DASHBOARD_ANALYTICS.md) | Real-Time Metrics & Reporting | Real SQL Aggregations, 60s Redis Caching, Recharts Visualizations, Skill Gaps |
| [**Frontend Architecture**](file:///docs/FRONTEND.md) | Client-Side Implementation | React 19, TypeScript, TanStack Router/Query, Tailwind CSS v4, Generative UI |
| [**Deployment & DevOps**](file:///docs/DEPLOYMENT.md) | Infrastructure & Containerization | Docker Compose, Multi-stage Dockerfiles, Nginx Reverse Proxy, Cloud Run/Render |
| [**Testing & Quality Assurance**](file:///docs/TESTING.md) | Test Suites & Automation | 35 Automated Pytest Suites, CI/CD GitHub Actions Workflow, Integrity Verification |
| [**Troubleshooting & Runbook**](file:///docs/TROUBLESHOOTING.md) | Operations & Incident Recovery | Connection Pool Server Drops, Corrupted ZIPs, Gemini Rate Limits, Health Checks |
| [**Changelog**](file:///docs/CHANGELOG.md) | Version Release History | Detailed Chronological Changelog spanning Phases 1 through 12 |
| [**Educator User Manual**](file:///docs/USER_MANUAL.md) | Non-Technical Guide | Step-by-Step Instructor Workflows, Rubric Setup, Review Queue, Export Walkthroughs |

---

## 2. Key Architectural Guarantees

1. **Zero Unapproved Grades:** AI suggestions are strictly draft recommendations (`draft_grades`). Grades only become official once an authorized educator clicks "Approve Grade" or enables explicit high-confidence auto-stamping.
2. **Deterministic Arithmetic:** Sub-criterion points are summed using pure-Python IEEE-754 arithmetic with 2-decimal rounding. The LLM is prohibited from performing score arithmetic internally.
3. **FERPA/GDPR Cryptographic Minimization:** All student personally identifiable information (PII) is encrypted at rest using AES-256 Fernet. When sent to external LLMs, submissions are pseudonymized into deterministic hashes (`STUDENT_A3F89B`).
4. **Formula Injection Defense:** All exported spreadsheet cells beginning with `=`, `+`, `-`, `@`, `\t`, or `\r` are sanitized with leading apostrophes to protect educators from CSV Command Injection (CWE-1236).
5. **30-Day Soft-Delete Retention:** Deleting any course, assignment, or student places the record in a recoverable 30-day trash bin before permanent physical purging across the database, disk, and cache.
