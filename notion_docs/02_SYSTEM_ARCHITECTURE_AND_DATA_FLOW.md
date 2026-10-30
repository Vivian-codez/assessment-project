# 🏛️ 02. System Architecture & Data Flow

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟢 Active  
> 📅 **Last Updated:** 2026-10-29  

---

## 🏗️ High-Level Architectural Topology

Verism AI is engineered as a decoupled modern web application with high-throughput asynchronous processing:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        CLIENT LAYER (Browser)                         │
│                                                                        │
│   TanStack Start / React 19 Frontend  (Vite + Tailwind CSS + Lucide)   │
│   - Real-time Dashboard           - Matrix Rubric Builder             │
│   - Submission Dropzone (PDF/ZIP) - Plagiarism Diff Inspector         │
│   - Review & Grade Stamping Queue - Live Gradebook Spreadsheet        │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                        HTTPS / JSON REST API (CORS)
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                     BACKEND APPLICATION CORE (FastAPI)                 │
│                                                                        │
│  ├── /api/v1/ Routers (Auth, Courses, Assignments, Grading, etc.)      │
│  ├── Core Middleware (CORS, JWT Bearer Auth, Request Auditing)         │
│  ├── Security & Privacy Layer (Fernet AES-128 Encryption & Redaction)  │
│  └── SQLAlchemy 2.0 ORM & Supabase Client Integration                  │
└──────────────┬──────────────────────────────┬──────────────────────────┘
               │                              │
      Synchronous Reads / Writes      Dispatches Async Jobs
               │                              │
               ▼                              ▼
┌─────────────────────────────┐ ┌────────────────────────────────────────┐
│      PERSISTENCE LAYER      │ │            ASYNC WORKER LAYER          │
│                             │ │                                        │
│  PostgreSQL / Supabase DB   │ │   Celery Worker Pool + Redis Broker    │
│  (Instructors, Classrooms,  │ │   - Batch File Extraction (ZIP/PDF)    │
│   Students, Submissions,    │ │   - Vector Generation & Indexing       │
│   Draft Grades, Audit Logs) │ │   - High-throughput Gemini Evaluation  │
└──────────────┬──────────────┘ └──────────────┬─────────────────────────┘
               │                               │
               │                               ▼
               │                ┌────────────────────────────────────────┐
               │                │          AI & VECTOR SERVICES          │
               │                │                                        │
               │                │  1. Qdrant Vector Engine:              │
               │                │     - 768-dim semantic embeddings      │
               │                │     - Sub-cohort cosine similarity     │
               │                │                                        │
               │                │  2. Google GenAI (Gemini 2.5 Flash):   │
               │                │     - Rubric Context Caching (2h TTL)  │
               │                │     - Structured Pydantic JSON Output  │
               │                │     - Multimodal PDF Token Inspection  │
               │                └────────────────────────────────────────┘
```

---

## 🔄 End-to-End Submission Pipeline (Sequence Flow)

```mermaid
sequenceDiagram
    autonumber
    actor Teacher as 👩‍🏫 Instructor
    participant FE as 🖥️ Frontend (React 19)
    participant API as ⚡ FastAPI Backend
    participant SEC as 🛡️ FERPA Sanitizer
    participant QDR as 🔎 Qdrant Vector DB
    participant CEL as ⚙️ Celery Worker
    participant GEM as 🤖 Gemini 2.5 Flash
    participant DB as 🗄️ PostgreSQL / Supabase

    Teacher->>FE: Uploads 50 student submissions (PDFs / ZIP)
    FE->>API: POST /api/v1/submissions/upload (multipart)
    API->>DB: Stores encrypted submission metadata
    API->>CEL: Dispatches evaluation_tasks.evaluate_batch(job_id)
    API-->>FE: Returns 202 Accepted + job_id (Polling enabled)
    
    rect rgb(240, 248, 255)
        Note over CEL,SEC: Privacy & Anonymization Step
        CEL->>SEC: Sanitize student text (Strip Name, Roll, Email)
        SEC-->>CEL: Return text with tokens: [STUDENT_TOKEN_1]
    end

    rect rgb(255, 250, 240)
        Note over CEL,QDR: Plagiarism Vector Step
        CEL->>QDR: Generate 768-dim dense embedding
        QDR->>QDR: Cosine cross-match against all cohort submissions
        QDR-->>CEL: Flag pairs with similarity > 90%
    end

    rect rgb(245, 255, 245)
        Note over CEL,GEM: AI Evaluation Step (Gemini)
        CEL->>GEM: Evaluate masked text against cached rubric
        GEM-->>CEL: Structured JSON (Scores, Criteria Rationales, AI Probability)
    end

    CEL->>DB: Persist Draft Grade (status: "DRAFT") + Similarity Matches
    CEL->>DB: Update batch job status to 100% Complete
    FE->>API: GET /api/v1/jobs/{job_id} -> Status: COMPLETED
    FE->>Teacher: Displays Review Queue with Draft Grades & Plagiarism Matrix
    Teacher->>FE: Adjusts points & clicks "Stamp Approval"
    FE->>API: POST /api/v1/grading/{submission_id}/stamp
    API->>DB: Mark status = "APPROVED", record in audit_logs
    API-->>FE: Grade published to live Gradebook
```

---

## 🧩 Component Responsibilities Matrix

| Subsystem | Technology | Responsibility | Failure Mode / Fallback |
| :--- | :--- | :--- | :--- |
| **Frontend UI** | React 19, TanStack Start, Tailwind | Teacher control panel, drag-and-drop batch upload, side-by-side diffing, live gradebook table | Client-side optimistic updates with retry toasts on network disruption |
| **Backend API** | FastAPI, Python 3.11+ | REST routing, authentication, request validation, cryptographic encryption, permission checks | Automatic 4xx/5xx structured error JSON schemas conforming to RFC 7807 |
| **Worker Queue** | Celery + Redis | Long-running asynchronous evaluation of batches (up to 200 submissions per batch) | Falls back to FastAPI `BackgroundTasks` if Redis is unreachable in local dev |
| **Vector DB** | Qdrant | Peer-to-peer semantic similarity cross-checks within assignment cohorts | In-memory `:memory:` fallback for rapid local prototyping without Docker |
| **LLM Engine** | Google GenAI (Gemini 2.5 Flash) | Criterion scoring, rationale generation, AI text stylometry estimation | Pre-compiled structured schemas guarantee 100% parseable JSON; automatic token backoff |
| **Persistence** | PostgreSQL (Supabase) + SQLite | Relational storage for users, courses, assignments, rubrics, submissions, and audit records | Development SQLite automatic schema bootstrapping via `seed_data.py` |
