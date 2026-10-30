# 🛠️ 08. Local Development & DevOps

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🟢 Active  
> 📅 **Last Updated:** 2026-10-29  

---

## 💻 Developer Prerequisites

Before running the application locally, ensure you have:
- **Python**: 3.11 or higher
- **Node.js**: 18.0 or higher (with `npm` or `bun`)
- **Docker & Docker Compose**: Recommended for running Redis and Qdrant locally
- **Google GenAI API Key**: Obtainable from [Google AI Studio](https://aistudio.google.com/)

---

## 🚀 Rapid Local Setup (Without Docker)

You can run the entire system directly on your workstation using SQLite and in-memory vector storage:

### 1. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize environment variables
cp .env.example .env

# Seed initial database with sample classrooms & rubrics
python scripts/seed_data.py

# Start the FastAPI development server with auto-reload
python app.py
```
> 🌐 Backend runs at: `http://localhost:8000`  
> 📄 Interactive OpenAPI docs: `http://localhost:8000/docs`

---

### 2. Frontend Setup

```bash
# Open a new terminal and navigate to frontend directory
cd frontend

# Install Node modules
npm install

# Start Vite development server
npm run dev
```
> 🖥️ Frontend runs at: `http://localhost:5173`

---

## 🐳 Local PostgreSQL Container (Docker Setup)

For local development and self-hosted deployments without external cloud dependencies, a standalone local PostgreSQL 16 container is configured via [docker-compose.yml](file:///c:/Users/alice/OneDrive/Desktop/Prototype/docker-compose.yml):

### 1. Database Service Configuration
- **Image:** `postgres:16-alpine` (lightweight, security-patched PostgreSQL 16)
- **Container Name:** `verism_postgres`
- **Exposed Port:** `5432:5432`
- **Default Database:** `verism_db`
- **Default User / Password:** `postgres` / `postgres`
- **Persistent Volume:** `postgres_data:/var/lib/postgresql/data`
- **Schema Auto-Init:** `./backend/init.sql:/docker-entrypoint-initdb.d/init.sql:ro` (automatically executed on clean container creation)
- **Healthcheck:** `pg_isready -U postgres -d verism_db` every 5 seconds

### 2. Docker Management Commands

```bash
# Start ONLY the local PostgreSQL database in the background:
docker compose up -d db

# Start the full stack (PostgreSQL + Redis + Qdrant + FastAPI + Celery + Frontend):
docker compose up -d

# View status and healthcheck of running containers:
docker compose ps

# Check PostgreSQL healthcheck directly:
docker exec verism_postgres pg_isready -U postgres -d verism_db

# Inspect database logs:
docker compose logs -f db

# Stop and remove containers (data preserved in volume):
docker compose down

# Stop and purge volume (WARNING: deletes all local data):
docker compose down -v
```

---

## 🔑 Environment & Connection Updates

### Local PostgreSQL Connection String:
```ini
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/verism_db
```

### Backend (`backend/.env`):
```ini
# Toggle cloud Supabase off; use local PostgreSQL + local JWT auth
USE_SUPABASE=false

# Local PostgreSQL connection string
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/verism_db
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
POSTGRES_DB=verism_db

# Local file storage (replaces Supabase Storage bucket)
UPLOADS_DIR=./uploads

# Authentication & FERPA Encryption
SECRET_KEY=verism_super_secret_jwt_key_change_in_production_1234567890
ACCESS_TOKEN_EXPIRE_MINUTES=1440
FERPA_ENCRYPTION_KEY=MbGUys4qem_FHtZy_5zx8bBSrxkTI2UWrjnhrFAHcyY=
```

### Frontend (`frontend/.env`):
```ini
VITE_API_BASE_URL=http://localhost:8000/api/v1
VITE_USE_SUPABASE=false
```

---

## 🧪 Migration Verification Script

An automated test script is provided in [`scripts/verify_migration.py`](file:///c:/Users/alice/OneDrive/Desktop/Prototype/scripts/verify_migration.py) to validate the end-to-end local setup:

```bash
# Run verification test:
backend\.venv\Scripts\python.exe scripts\verify_migration.py
```

The script verifies:
1. `USE_SUPABASE=false` flag and local `DATABASE_URL` format.
2. Supabase conditional stub gracefully intercepts calls without unhandled errors.
3. All 12 core tables exist in the SQLAlchemy ORM metadata (`users`, `user_sessions`, `instructors`, `courses`, `rubrics`, `rubric_criteria`, `assignments`, `submissions`, `draft_grades`, `similarity_matches`, `batch_jobs`, `audit_logs`).
4. All 128 REST API endpoints are registered on FastAPI.
5. Complete local JWT lifecycle: user registration (`POST /api/v1/auth/signup`), profile retrieval (`GET /api/v1/auth/me`), and login (`POST /api/v1/auth/login`).

---

## ☁️ Deployment Guide (Render & Cloud Platforms)

The repository includes a ready-to-deploy [`render.yaml`](file:///c:/Users/alice/OneDrive/Desktop/Prototype/render.yaml) specification:

1. Connect your GitHub repository to [Render.com](https://render.com/).
2. Select **Blueprints** and point to `render.yaml`.
3. Set the required secret environment variables (`GEMINI_API_KEY`, `FERPA_ENCRYPTION_KEY`, `SECRET_KEY`).
4. Render automatically provisions:
   - Web Service for FastAPI Backend
   - Background Worker for Celery
   - Managed Redis Instance
   - Static / SSR Site for Vite Frontend
