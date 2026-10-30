# 🏛️ Verism AI — Engineering & Product Notion Workspace

> 💡 **Welcome to the Verism AI Engineering Hub!**
> This Notion Workspace serves as the single source of truth for all architectural decisions, API specifications, FERPA compliance protocols, database schemas, and frontend/backend implementation guides for **Verism AI** (EduCheck AI).

---

## 🧭 Quick Navigation Index

| Page | Description | Primary Audience | Live Notion Link |
| :--- | :--- | :--- | :--- |
| **01. Executive Summary & Vision** | Product vision, core problem statement, and "AI suggests, You stamp" philosophy | Product, Leadership, All | [Open in Notion](https://notion.so/408843bd66f181d69dcec2ba231518f9) |
| **02. System Architecture & Data Flow** | End-to-end data pipelines, micro-architecture, and sequence diagrams | Engineers, Architects | [Open in Notion](https://notion.so/408843bd66f1812a82ebe97f1452fa48) |
| **03. Backend Service Guide** | FastAPI core, Celery async queue, Qdrant vectors, Gemini GenAI | Backend Developers | [Open in Notion](https://notion.so/408843bd66f18175bccfe161a11c2390) |
| **04. Frontend Application Guide** | React 19, TanStack Start/Router, Tailwind UI, Matrix Rubric Builder | Frontend Developers | [Open in Notion](https://notion.so/408843bd66f18167869eebc79edb33a0) |
| **05. API Reference & Endpoints** | REST API v1 catalog, schemas, error codes, and curl examples | Full Stack, Integrators | [Open in Notion](https://notion.so/408843bd66f1813ab6e6d8d5dfd3b643) |
| **06. Database Schema & ERD** | PostgreSQL/Supabase tables, relationships, indexes, and migrations | DBAs, Backend | [Open in Notion](https://notion.so/408843bd66f181beb967d41e8d979dcd) |
| **07. FERPA Security & Compliance** | AES-128 Fernet encryption, LLM PII pseudonymization, and audit logs | Security, Legal, Devs | [Open in Notion](https://notion.so/408843bd66f1813abb6ef38fde47fe67) |
| **08. Local Development & DevOps** | Docker Compose setup, environment configuration, and Render deployment | DevOps, All Engineers | [Open in Notion](https://notion.so/408843bd66f181418932ccb97b686bae) |
| **09. Roadmap & Sprint Tracker** | Notion database formatted sprint backlog, completed epics, and Q4 goals | Product, Team Leads | [Open in Notion](https://notion.so/408843bd66f1818eb120d55b54f7eaa7) |
| **10. Notion Import Guide** | Step-by-step instructions for importing these docs into your live Notion space | All Team Members | [Open in Notion](https://notion.so/408843bd66f181c1ba70cc13bf430964) |

---

---

## ⚡ Project Fast Facts

> 🏷️ **Platform Name:** Verism AI (formerly EduCheck AI)  
> 🎓 **Domain:** Higher Education EdTech, AI-Assisted Assessment & Academic Integrity  
> 🔒 **Security Standard:** FERPA & GDPR Compliant (Zero Student PII exposed to external LLMs)  
> 🤖 **AI Engine:** Google Gemini 2.5 Flash / Pro via Google GenAI SDK (with Context Caching)  
> 🔎 **Vector Engine:** Qdrant (768-dim dense cross-submission similarity matching)  
> 🌐 **Frontend Stack:** React 19, TanStack Router / TanStack Start, Vite, Tailwind CSS  
> ⚙️ **Backend Stack:** Python 3.11+, FastAPI, Celery, Redis, SQLAlchemy 2.0, Supabase PostgreSQL  

---

## 🎯 Core Operating Principles

1. **"AI Suggests, You Stamp"**  
   AI models generate preliminary scores and rubric feedback, but **no grade is ever finalized** without explicit instructor review, potential override, and human approval stamping.
2. **Deterministic Student Anonymization**  
   Before text leaves the university boundary to Gemini or any third-party model, raw PII (`name`, `roll_number`, `email`) is scrubbed into deterministic pseudonym tokens (`[STUDENT_HASH]`).
3. **Multi-Vector Integrity Verification**  
   Plagiarism detection combines:
   - **Peer-to-Peer Dense Vectors**: Semantic cross-submission cosine similarity via Qdrant.
   - **AI Stylometry Probability**: Sentence-level synthetic text markers.
   - **Side-by-Side Highlight Diffs**: Verbatim phrase matching with synchronized scroll inspection.

---

## 🛠️ Notion Workspace Setup Tips

* **To import this entire documentation into Notion:**
  1. Open your Notion Workspace.
  2. Click **Import** in the left sidebar.
  3. Select **Markdown & CSV** and choose these Markdown files from the `notion_docs/` directory.
  4. Alternatively, use the automated sync script:
     ```bash
     python scripts/export_to_notion.py --token YOUR_NOTION_INTEGRATION_TOKEN --parent-page YOUR_PAGE_ID
     ```
* **Recommended Notion Layout:**
  - Set this page as the **Default Team Wiki Home**.
  - Enable **Full Width** in page settings for optimal reading of tables and architecture diagrams.
  - Pin the **Roadmap & Sprint Tracker** to your team's quick favorites.
