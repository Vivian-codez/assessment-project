# REST API Reference & Endpoint Catalog

The Verism AI backend exposes a fully documented, OpenAPI v3-compliant RESTful interface under `/api/v1`.

---

## 1. Authentication & Security Headers

All requests to private endpoints require an `Authorization` header containing a valid JWT Bearer token:
```http
Authorization: Bearer <jwt_access_token>
```
Alternatively, browser clients utilize secure HttpOnly session cookies set via `POST /api/v1/auth/login`.

### Enterprise Security Headers
Every HTTP response automatically includes:
```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Referrer-Policy: strict-origin-when-cross-origin
```

---

## 2. API Endpoint Directory

### 2.1 Course Management
- `GET /api/v1/courses`: List all active courses for the authenticated instructor.
- `POST /api/v1/courses`: Create a new academic course.
  ```json
  {
    "name": "Operating Systems",
    "code": "CS-301",
    "section": "A",
    "tone": "lav"
  }
  ```
- `GET /api/v1/courses/{course_id}`: Retrieve course details and statistics.
- `DELETE /api/v1/courses/{course_id}`: Move course to 30-day Trash Bin (soft delete).

### 2.2 Assignments & Evaluation Folders
- `GET /api/v1/courses/{course_id}/assignments`: Retrieve all assignments configured for a course.
- `POST /api/v1/courses/{course_id}/assignments`: Create assignment with rubric and reference solution.
  ```json
  {
    "title": "Lab 2: Virtual Memory & Paging",
    "description": "Implement an LRU page replacement algorithm.",
    "max_score": 100.0,
    "starter_code": "def lru_page_fault(pages, capacity): pass",
    "reference_solution": "def lru_page_fault(pages, capacity):\n    # Canonical implementation...",
    "rubric_text": "Criteria: Correctness (40), Complexity (30), Code Quality (20), Tests (10)"
  }
  ```
- `DELETE /api/v1/assignments/{assignment_id}`: Soft delete assignment to 30-day trash.

### 2.3 Submissions & Multi-Format Ingestion
- `POST /api/v1/assignments/{assignment_id}/submissions`: Upload single or multi-student submissions (PDF, DOCX, ZIP, PY, C, CPP, JAVA).
  - Content-Type: `multipart/form-data`
  - Parameters: `file` (`UploadFile`), `student_identifier` (optional).
  - Returns `201 Created` with extracted text length and parsed student roll number.
- `GET /api/v1/assignments/{assignment_id}/submissions`: List submissions with evaluation status and integrity metrics.
- `DELETE /api/v1/submissions/{submission_id}`: Soft delete submission.

### 2.4 AI Auto-Grading & Teacher Stamping
- `POST /api/v1/assignments/{assignment_id}/evaluate`: Enqueue batch evaluation job for unprocessed submissions.
  - Returns `202 Accepted` with `{ "job_id": "job-...", "total_submissions": 45 }`.
- `POST /api/v1/grading/stamp/{submission_id}`: Teacher approves AI draft recommendation.
  ```json
  {
    "final_score": 92.5,
    "teacher_notes": "Great edge case coverage on inverted page tables."
  }
  ```
  - Emits immutable FERPA audit log entry and marks `is_stamped = True`.

### 2.5 Real-Time SQL Analytics (`/api/v1/analytics`)
- `GET /api/v1/analytics`: Query real-time SQL aggregated metrics with 60-second Redis caching.
  - Query Parameters: `course_id` (optional), `assignment_id` (optional), `date_range` (`all`, `7d`, `30d`, `90d`).
  - Response Schema:
    ```json
    {
      "course_id": "CS101",
      "course_name": "Data Structures",
      "course_code": "CS-101",
      "date_range": "30d",
      "kpi_cards": {
        "average_score": { "value": "84.2%", "trend": "+3.2% vs prior", "tone": "lav" },
        "pending_reviews": { "value": "6", "trend": "6 actionable", "tone": "amber" },
        "similarity_flags": { "value": "1", "trend": "AST winnowing", "tone": "clay" },
        "on_time_rate": { "value": "92.0%", "trend": "+2.0%", "tone": "sage" }
      },
      "grade_distribution": [
        { "bucket": "0-59", "count": 1, "percentage": 10.0 },
        { "bucket": "60-69", "count": 2, "percentage": 20.0 },
        { "bucket": "70-79", "count": 2, "percentage": 20.0 },
        { "bucket": "80-89", "count": 3, "percentage": 30.0 },
        { "bucket": "90-100", "count": 2, "percentage": 20.0 }
      ],
      "assignment_trends": [...],
      "criterion_averages": [...],
      "submission_funnel": [...],
      "needs_attention": [...],
      "is_empty": false
    }
    ```
- `POST /api/v1/analytics/demo-data`: Populate sandbox course (`CS101-SANDBOX`) with 10 students, 2 assignments, rubrics, and similarity collisions.
- `DELETE /api/v1/analytics/demo-data`: Purge sandbox demo data and flush analytics cache.

### 2.6 Gradebook & RFC-4180 Exports
- `GET /api/v1/courses/{course_id}/export/csv`: Export RFC-4180 CSV gradebook with UTF-8 BOM (`\ufeff`) and CWE-1236 injection defense.
  - Query Parameters: `mode` (`draft` or `final`), `format` (`default`, `google_classroom`, `moodle`), `assignment_id` (optional).
  - Injects `Content-Disposition: attachment; filename="CS-101_final_default.csv"`.
- `GET /api/v1/courses/{course_id}/export/xlsx`: Export multi-tab Excel workbook formatted via openpyxl with SHA-256 cryptographic audit checksum.

### 2.7 30-Day Trash Bin & Data Governance
- `GET /api/v1/trash`: List all soft-deleted entities across Courses, Assignments, Submissions, Students, Rubrics with days remaining.
- `POST /api/v1/trash/restore/{entity_type}/{entity_id}`: Restore soft-deleted item from trash bin.
- `DELETE /api/v1/trash/permanent/{entity_type}/{entity_id}`: Permanent cascade purge across database, disk storage, and Redis cache.
- `GET /api/v1/user/export-all-data`: Stream complete educator data archive as a ZIP file (courses, assignments, students, submissions, audit logs).
- `GET /api/v1/privacy/me`: Retrieve educator GDPR/DPDP privacy profile and sub-processor commitments.
- `POST /api/v1/privacy/erasure-request`: Submit formal GDPR Article 17 / DPDP Section 12 erasure ticket.
- `GET /api/v1/legal/privacy`, `/legal/terms`, `/legal/dpa`: Fetch institutional legal compliance documentation.
