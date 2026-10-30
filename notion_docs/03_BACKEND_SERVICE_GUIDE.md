# ⚙️ 03. Backend Service Guide

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟢 Active  
> 📅 **Last Updated:** 2026-10-29  

---

## 🏛️ Architecture Overview

The Verism AI backend is built with **FastAPI** on Python 3.11+, following clean architecture patterns:
- Separation of API endpoints (`app/api/v1/`)
- Declarative data models (`app/models/`)
- Pydantic v2 schemas (`app/schemas/`)
- Specialized business logic services (`app/services/`)
- Distributed asynchronous task execution (`app/workers/`)

```
backend/
├── app/
│   ├── api/v1/          # REST Routers (auth, classrooms, submissions, etc.)
│   ├── core/            # Configuration, database connection, security & cryptography
│   ├── models/          # SQLAlchemy 2.0 ORM database entities
│   ├── schemas/         # Pydantic v2 request & response schemas
│   ├── services/        # Gemini, Qdrant, PDF parser, FERPA, Supabase
│   └── workers/         # Celery task definitions & task runner
├── scripts/             # Database seeders, benchmark runners, utilities
├── Dockerfile           # Production container definition
├── docker-compose.yml   # Multi-service stack (API, DB, Redis, Qdrant)
└── requirements.txt     # Python runtime dependencies
```

---

## 🤖 Google GenAI (Gemini 2.5 Flash / Pro) Integration

The `GeminiService` (`app/services/gemini_service.py`) handles all AI evaluation tasks.

### 1. Structured JSON Schema Output
To eliminate hallucinated formatting or unparseable text, the backend enforces native Pydantic JSON schemas via the Gemini `response_schema` configuration:

```python
class CriterionScore(BaseModel):
    criterion_name: str
    points_awarded: float
    max_points: float
    rationale: str
    suggestions_for_improvement: str

class StructuredGradingOutput(BaseModel):
    overall_score: float
    max_score: float
    percentage: float
    overall_feedback: str
    criteria_breakdown: List[CriterionScore]
    ai_content_probability: float  # 0.0 - 100.0%
    flags: List[str]
```

### 2. Context Caching (Cost & Speed Optimization)
When evaluating batches of 50–200 submissions against a complex assignment rubric (e.g., 5 pages of criteria and syllabus policies), transmitting the rubric tokens repeatedly is slow and expensive.

Verism AI leverages **Gemini Context Caching**:
```python
cache = client.caches.create(
    model="gemini-flash-latest",
    config=types.CreateCachedContentConfig(
        contents=[rubric_text, assignment_prompt],
        display_name=f"rubric_{assignment_id}",
        ttl="7200s", # 2-hour TTL
    )
)
```
> 💰 **Impact:** Context caching reduces prompt token overhead by **up to 75%** and lowers latency per submission from ~8.5 seconds down to ~2.1 seconds.

---

## 🔎 Qdrant Vector Plagiarism Engine

The `VectorService` (`app/services/vector_service.py`) manages dense semantic embeddings to identify unauthorized peer collaboration:

1. **Embedding Generation**: Text is transformed into 768-dimensional dense vectors using Google's text-embedding models.
2. **Batch Payload Ingestion**: Each submission vector is indexed in Qdrant with metadata filters (`assignment_id`, `classroom_id`, `submission_id`).
3. **Cross-Cohort Pairwise Cosine Search**:
   ```python
   # Query Qdrant for neighbors above the threshold within the same assignment
   results = qdrant_client.search(
       collection_name="verism_submissions",
       query_vector=submission_vector,
       query_filter=models.Filter(
           must=[models.FieldCondition(key="assignment_id", match=models.MatchValue(value=assignment_id))]
       ),
       score_threshold=0.85, # 85% similarity threshold
       limit=20
   )
   ```
4. **Verbatim Highlight Extraction**: For flagged pairs, a lightweight longest-common-subsequence (LCS) algorithm extracts verbatim overlapping sentence fragments for side-by-side inspection on the frontend.

---

## ⚙️ Celery Async Worker Pipeline

For large classroom rosters (e.g., 100 students submitting 10-page final term papers simultaneously), synchronous HTTP processing would cause gateway timeouts.

The asynchronous pipeline (`app/workers/evaluation_tasks.py`) operates as follows:
- When submissions are uploaded, the endpoint immediately commits records to the database and returns `202 Accepted` with a `job_id`.
- The Celery worker processes each submission sequentially or in concurrent sub-tasks:
  1. PDF text extraction & OCR (if scanned).
  2. FERPA redaction of student identifiers.
  3. Qdrant vector indexing and peer-to-peer cross-match.
  4. Gemini structured grading evaluation.
  5. Atomic draft grade record creation in PostgreSQL.
- Progress updates (`current_index / total_count`) are published to Redis, enabling the frontend progress bar to update smoothly from 0% to 100%.

---

## 🛡️ Core Settings & Configuration

Settings are dynamically resolved via Pydantic Settings v2 in `app/core/config.py`:

| Setting | Default Value | Description |
| :--- | :--- | :--- |
| `API_V1_STR` | `/api/v1` | Base route prefix for all endpoints |
| `DATABASE_URL` | `sqlite:///verism.db` / `postgresql://...` | Relational database connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery message broker and result cache |
| `QDRANT_URL` | `:memory:` (or `http://localhost:6333`) | Qdrant vector database URL |
| `FERPA_ENCRYPTION_KEY` | *(URL-safe base64 Fernet key)* | AES-128 key for student PII encryption |
| `GEMINI_MODEL` | `gemini-flash-latest` | Primary LLM model for fast, structured grading |
| `DEFAULT_SIMILARITY_THRESHOLD` | `90.0` | Default peer-to-peer plagiarism alert trigger |
