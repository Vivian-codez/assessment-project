# Verism AI — AI Assessment & Integrity Platform

An enterprise-grade, FERPA-compliant assessment, grading, and plagiarism verification system built for higher education. Features 3-way plagiarism detection (peer-to-peer vector similarity, AI content probability, and public web grounding) with human-in-the-loop teacher review.

---

## 🏛️ System Architecture

```
                                  ┌───────────────────────────────┐
                                  │   TanStack Start / React 19   │
                                  │   (Vite + Tailwind CSS UI)    │
                                  └───────────────┬───────────────┘
                                                  │ REST API
                                                  ▼
                                  ┌───────────────────────────────┐
                                  │      FastAPI Backend Core     │
                                  │     (FERPA / GDPR Shield)     │
                                  └───────┬───────────────┬───────┘
                                          │               │
                 ┌────────────────────────┼───────────────┼────────────────────────┐
                 ▼                        ▼               ▼                        ▼
       ┌───────────────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌───────────────────┐
       │   Google Gemini   │    │  Qdrant Vector   │    │ PostgreSQL / DB  │    │  Redis + Celery   │
       │ Flash Evaluation  │    │  Cosine Matching │    │ & Supabase Sync  │    │  Batch Processing │
       └───────────────────┘    └──────────────────┘    └──────────────────┘    └───────────────────┘
```

### 1. Frontend (`/frontend`)
* **Framework**: React 19, Vite, TanStack Router / TanStack Start
* **Styling**: TailwindCSS, Radix UI primitives, Lucide icons
* **Features**:
  * Real-time course dashboard & assignment management
  * Drag-and-drop batch submission uploader (PDF, TXT, DOCX, ZIP)
  * Interactive 3-way plagiarism inspection matrix
  * AI evaluation & rubric-based grading queue
  * Teacher Grade Stamping (AI grades remain draft until instructor stamps approval)
  * Live spreadsheet gradebook with CSV export

### 2. Backend (`/backend`)
* **Framework**: FastAPI (Python 3.11+)
* **Database**: PostgreSQL / SQLite with SQLAlchemy 2.0 ORM & Supabase layer
* **Vector DB**: Qdrant for semantic cross-submission vector embeddings
* **Task Queue**: Celery with Redis broker (with fallback async background tasks)
* **AI Engine**: Google GenAI (Gemini Flash) with structured JSON evaluation schemas
* **Compliance**: Cryptographic FERPA/GDPR encryption (Fernet AES-128-CBC) of student PII (name, roll, email)

---

## 🚀 Quickstart Guide

### Prerequisites
* Python 3.11+
* Node.js 18+ & npm
* Docker (optional, for Redis & Qdrant)

### 1. Start Backend

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env

# Seed initial database records
python scripts/seed_data.py

# Run FastAPI server
python app.py  # or python run.py
# Backend runs at: http://localhost:8000
# OpenAPI Docs: http://localhost:8000/docs
```

### 2. Start Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
# Frontend runs at: http://localhost:5173
```

---

## 🛡️ Security & FERPA Compliance

* **Transparent Field-Level Encryption**: Student identifiers (`student_name`, `student_roll`, `student_email`) are encrypted at rest using URL-safe Fernet cryptography.
* **AI Sanitization**: Raw student PII is masked into deterministic pseudonyms (`[STUDENT_NAME]`, `[STUDENT_ROLL]`) prior to sending text to LLM inference endpoints.
* **Audit Trail**: Every grade override, approval stamp, and flag dismissal is recorded in immutable audit logs.

---

## 🧪 Testing

Run backend test suite:
```bash
cd backend
pytest
```

Run frontend type check & build:
```bash
cd frontend
npx tsc --noEmit
npm run build
```

---

## 📄 License
MIT License. Built for educational and research prototyping.
