# 📡 05. API Reference & Endpoints

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟢 Active  
> 📅 **Last Updated:** 2026-10-29  
> 🌐 **Base URL:** `http://localhost:8000/api/v1`  
> 📖 **OpenAPI Docs:** `http://localhost:8000/docs`  

---

## 🔐 Authentication & Authorization

All non-public endpoints require an HTTP Bearer JWT token in the `Authorization` header:
```http
Authorization: Bearer <your_jwt_access_token>
```

---

## 📋 Endpoint Catalog by Domain

### 1. Authentication & Instructor Profile (`/auth`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `POST` | `/auth/register` | Register a new instructor account | No |
| `POST` | `/auth/login` | Authenticate instructor & issue JWT access token | No |
| `GET` | `/auth/me` | Fetch active instructor profile & preferences | Yes |
| `PUT` | `/auth/preferences` | Update instructor grading preferences | Yes |

#### Sample Request: Login
```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
     -H "Content-Type: application/json" \
     -d '{"email": "instructor@university.edu", "password": "SecretPassword123"}'
```

---

### 2. Classrooms & Courses (`/classrooms` & `/courses`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/classrooms` | List all classrooms for current instructor | Yes |
| `POST` | `/classrooms` | Create a new classroom course | Yes |
| `GET` | `/classrooms/{id}` | Get classroom details by UUID | Yes |
| `GET` | `/classrooms/{id}/students` | List all enrolled students in classroom | Yes |
| `POST` | `/classrooms/{id}/students` | Add single student to classroom roster | Yes |
| `POST` | `/classrooms/{id}/students/bulk` | Bulk import students via CSV/JSON list | Yes |
| `DELETE` | `/classrooms/{id}/students/{student_id}` | Remove student from classroom | Yes |

---

### 3. Assignments (`/assignments`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/assignments` | List assignments (filterable by `course_id`) | Yes |
| `POST` | `/assignments` | Create a new assignment with attached rubric | Yes |
| `GET` | `/assignments/{id}` | Retrieve assignment metadata & attached rubric | Yes |
| `PUT` | `/assignments/{id}` | Update assignment title, prompt, or due date | Yes |
| `DELETE` | `/assignments/{id}` | Delete assignment & associated submissions | Yes |

---

### 4. Rubrics (`/rubrics`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/rubrics` | List instructor's saved rubrics | Yes |
| `POST` | `/rubrics` | Create a new multi-criteria rubric | Yes |
| `GET` | `/rubrics/{id}` | Get rubric criteria & performance level matrix | Yes |
| `PUT` | `/rubrics/{id}` | Update rubric criteria weights and descriptions | Yes |

#### Sample Rubric Payload:
```json
{
  "name": "Research Term Paper Rubric",
  "assignment_id": "assignment-uuid-123",
  "criteria": [
    {
      "name": "Thesis & Argumentation",
      "max_points": 30.0,
      "description": "Clarity of thesis statement and logical progression of supporting arguments."
    },
    {
      "name": "Evidence & Citation",
      "max_points": 40.0,
      "description": "Integration of primary sources and accuracy of APA/MLA citations."
    },
    {
      "name": "Clarity & Style",
      "max_points": 30.0,
      "description": "Sentence structure, vocabulary precision, and grammatical accuracy."
    }
  ]
}
```

---

### 5. Submissions & Batch Upload (`/submissions`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/submissions` | List submissions for an assignment | Yes |
| `POST` | `/submissions/upload` | Upload single or multi-file submission (PDF/DOCX) | Yes |
| `POST` | `/submissions/batch-upload` | Upload `.zip` archive containing student cohort papers | Yes |
| `GET` | `/submissions/{id}` | Get decrypted submission details and raw file link | Yes |

---

### 6. AI Grading & Human-in-the-Loop Review (`/grading`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/grading/queue/{assignment_id}` | Retrieve pending submissions awaiting teacher review | Yes |
| `GET` | `/grading/{submission_id}` | Get draft grade, rubric points breakdown, and AI content probability | Yes |
| `PUT` | `/grading/{submission_id}/override` | Adjust points on specific criteria or add teacher notes | Yes |
| `POST` | `/grading/{submission_id}/stamp` | **Stamp Teacher Approval** (Transitions grade from `DRAFT` to `APPROVED`) | Yes |
| `POST` | `/grading/batch-stamp` | Stamp approval for multiple submissions in bulk | Yes |

---

### 7. Peer-to-Peer Similarity & Plagiarism (`/similarity`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/similarity/{assignment_id}/matches` | List flagged student pairs with similarity > threshold | Yes |
| `GET` | `/similarity/compare/{match_id}` | Side-by-side text comparison with highlighted matching phrases | Yes |
| `POST` | `/similarity/{match_id}/dismiss` | Dismiss flag as benign (e.g., shared template code) | Yes |

---

### 8. Async Jobs & Live Gradebook (`/jobs` & `/gradebook`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/jobs/{job_id}` | Poll progress (0–100%) and status of background batch evaluations | Yes |
| `GET` | `/gradebook/{assignment_id}` | Retrieve full cohort spreadsheet matrix | Yes |
| `GET` | `/gradebook/{assignment_id}/export.csv` | Stream downloadable CSV for school registrar / LMS | Yes |

---

### 9. FERPA & GDPR Audit Logs (`/audit`)

| Method | Endpoint | Description | Auth Required |
| :--- | :--- | :--- | :--- |
| `GET` | `/audit/logs` | Query immutable audit log records (grade edits, approvals, decrypt events) | Yes (Admin/Instructor) |
