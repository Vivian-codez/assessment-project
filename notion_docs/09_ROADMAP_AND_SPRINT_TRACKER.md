# 🗺️ 09. Roadmap & Sprint Tracker

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟡 Active Sprint  
> 📅 **Last Updated:** 2026-10-29  

---

## 📊 Sprint Board (Notion Database Format)

> 💡 *When importing into Notion, you can convert this table directly into a **Notion Kanban Board** grouped by `Status` or `Epic`.*

| Task / Feature | Epic | Assignee | Priority | Estimate | Status | Target Release |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Matrix Rubric Builder UI** | Frontend | Lead Frontend | 🔴 High | 5 pts | 🟢 Completed | v1.0.0 |
| **Drag & Drop Batch Submission Upload** | Frontend | Fullstack | 🔴 High | 5 pts | 🟢 Completed | v1.0.0 |
| **FERPA AES-128 Cryptography Layer** | Security | Lead Backend | 🔴 Critical | 8 pts | 🟢 Completed | v1.0.0 |
| **Gemini Structured JSON Schema Output** | AI Engine | AI Engineer | 🔴 High | 5 pts | 🟢 Completed | v1.0.0 |
| **Gemini Context Caching (2h TTL)** | AI Engine | AI Engineer | 🟡 Medium | 3 pts | 🟢 Completed | v1.0.0 |
| **Qdrant Dense Cosine Plagiarism Matching** | Vector / Plagiarism | Backend | 🔴 High | 8 pts | 🟢 Completed | v1.0.0 |
| **Human "Stamp Approval" Workflow** | Core Product | Fullstack | 🔴 High | 5 pts | 🟢 Completed | v1.0.0 |
| **Live Spreadsheet Gradebook + CSV Export** | Gradebook | Frontend | 🟡 Medium | 3 pts | 🟢 Completed | v1.0.0 |
| **Canvas LMS LTI 1.3 Integration** | Integrations | Lead Backend | 🔴 High | 8 pts | 🟡 In Progress | v1.1.0 |
| **Blackboard & Moodle Grade Sync** | Integrations | Backend | 🟡 Medium | 5 pts | 🔵 Backlog | v1.2.0 |
| **Multi-Language Essay Support (ES, FR, DE)** | AI Engine | AI Engineer | 🟢 Low | 3 pts | 🔵 Backlog | v1.2.0 |
| **Audio/Voice Feedback Recording for Teachers** | Frontend | Frontend | 🟢 Low | 5 pts | 🔵 Backlog | v1.3.0 |
| **Custom Institutional Single Sign-On (SAML/Okta)** | Security | DevOps | 🔴 High | 8 pts | 🟡 In Progress | v1.1.0 |

---

## 🎯 Epics & Milestones Overview

### 🏁 Milestone 1: Core Engine & Assessment MVP (v1.0.0 — Completed)
- [x] Functional FastAPI backend with SQLite/PostgreSQL support.
- [x] Multi-criteria dynamic rubric builder.
- [x] Batch PDF and ZIP archive submission processor.
- [x] Google GenAI (Gemini 2.5 Flash) integration with structured Pydantic schemas.
- [x] 768-dim Qdrant vector cross-check for unauthorized peer collaboration.
- [x] AES-128 Fernet field-level encryption for student PII.
- [x] Teacher Review queue with single-click grade stamping.
- [x] Downloadable gradebook CSV export.

---

### 🚀 Milestone 2: Enterprise LMS & Institutional Scale (v1.1.0 — Active Sprint)
- [ ] **Canvas LMS LTI 1.3 Integration**:
  - Direct roster sync from Canvas Course sections.
  - Automatic push of stamped grades back into Canvas Gradebook column.
- [ ] **Institutional Single Sign-On (SSO)**:
  - SAML 2.0 / Okta / Azure AD integration for faculty logins.
- [ ] **Multi-Section TA Role Permissions**:
  - Assign Teaching Assistants to specific sections (e.g., Section A vs. Section B).
  - Head Professor oversight dashboard for TA scoring consistency.

---

### 🔮 Milestone 3: Advanced Multimodal & Audio Feedback (v1.2.0 — Planning)
- [ ] **Audio/Voice Grading Dictation**: Allow professors to record 30-second voice memos that get attached to student feedback and transcribed automatically.
- [ ] **Diagram & Formula Inspection**: Multimodal grading of handwritten mathematics, circuit diagrams, and chemistry formulas via Gemini Pro Vision.
- [ ] **Longitudinal Student Growth Analytics**: Visualize student improvement across 5 consecutive essay assignments over an academic term.

---

## 🐛 Known Issues & Technical Debt Tracker

| Issue ID | Component | Severity | Description | Status |
| :--- | :--- | :--- | :--- | :--- |
| `TECH-101` | Celery | Low | If Redis container restarts, in-flight polling tasks require client refresh. | Mitigated with polling exponential backoff |
| `TECH-102` | Qdrant | Low | Embedded `:memory:` mode does not persist vector collections across server reboots. | Resolved by setting Docker Qdrant volume in production |
| `TECH-103` | PDF Parser | Medium | Scanned PDF images without OCR text require fallback to Gemini Multimodal bytes. | Integrated in `pdf_service.py` |
