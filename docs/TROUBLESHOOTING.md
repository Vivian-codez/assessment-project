# Operations & Incident Troubleshooting Runbook

> **Core Philosophy:** *"AI suggests. You stamp. Every grade waits for your approval."*  
> **Module Version:** 2.4.0  
> **Target Audience:** DevOps Engineers, Site Reliability Engineers, and System Administrators

---

## 1. Quick Diagnostic Cheat Sheet

| Symptom | Probable Root Cause | Resolution Action |
| :--- | :--- | :--- |
| **"Database connection dropped"** or `OperationalError: server closed the connection unexpectedly` | Cloud proxy or hosting firewall terminated idle TCP socket. | Verify `pool_pre_ping=True`, `pool_recycle=1800`, and TCP keepalive connect arguments in `session.py`. |
| **"Gemini Rate Limit Exceeded (HTTP 429)"** | Quota exhaustion on high-throughput batch grading. | System automatically retries with exponential backoff. Increase quota in Google Cloud Console or add secondary API key. |
| **Celery Tasks Hanging / Submissions Stuck in "Processing"** | Celery worker crashed, OOMed, or lost Redis connection. | Inspect `docker logs verism_celery_worker` and restart worker container with concurrency adjusted. |
| **CSV opens with garbled characters in Excel** | Missing Byte Order Mark (BOM). | Verify UTF-8 BOM (`\ufeff`) is prepended to CSV stream in `export_service.py`. |
| **Accidental Course or Assignment Deletion** | Instructor accidentally deleted record. | Open **Settings -> 30-Day Trash Bin** and click **Restore**. |

---

## 2. In-Depth Incident Scenarios & Remediation

### 2.1. Scenario A: Database Connection Severing & Resilience Pool
**Symptoms:** Under burst traffic, API logs report:
```text
sqlalchemy.exc.OperationalError: (psycopg2.OperationalError) SSL SYSCALL error: EOF detected
```
**Remediation Steps:**
1. Check database connectivity:
   ```bash
   docker exec -it verism_postgres pg_isready -U verism_admin -d verism_db
   ```
2. Inspect `backend/app/db/session.py` to ensure the connection pool is configured with:
   - `pool_pre_ping=True`: Tests the socket using `SELECT 1` before issuing application queries.
   - `pool_recycle=1800`: Re-establishes connections every 30 minutes to stay ahead of NAT firewall timeouts.
   - `connect_args` enabling TCP keepalive:
     ```python
     connect_args = {
         "keepalives": 1,
         "keepalives_idle": 30,
         "keepalives_interval": 10,
         "keepalives_count": 5
     }
     ```

---

### 2.2. Scenario B: Gemini AI Quota & Rate Limiting Backoff
**Symptoms:** Submissions fail during batch grading with status `failed` or HTTP 429.
**Remediation Steps:**
1. Verism AI includes built-in exponential jittered backoff in `backend/app/services/gemini_service.py`:
   - Retries up to 4 times with intervals: $2\text{s} \to 4\text{s} \to 8\text{s} \to 16\text{s}$.
2. If quota is persistently exhausted:
   - Verify `GEMINI_API_KEY` is active with billing enabled.
   - For offline grading, batch size can be throttled in Celery worker configuration:
     ```bash
     celery -A app.core.celery_app worker -Q grading --concurrency=2 --rate-limit=10/m
     ```

---

### 2.3. Scenario C: Corrupted Submissions & ZIP Bomb Protection
**Symptoms:** Submission ingestion worker memory spikes or hangs indefinitely.
**Remediation Steps:**
1. Verify that `ingestion_service.py` enforces maximum decompression limits:
   - Max file size: 50MB per single document.
   - Max archive uncompressed volume: 200MB.
   - Max file count per ZIP: 250 files.
2. If a student submits an encrypted or password-protected PDF:
   - The parser flags the submission as `unreadable_format` with clear UI guidance for the instructor to request a resubmission.

---

## 3. Useful Healthcheck & Inspection Commands

### Check Live System Health
```bash
curl -f http://localhost:8000/health
```
Expected response:
```json
{
  "status": "healthy",
  "database": "connected",
  "redis": "connected",
  "version": "2.4.0"
}
```

### Inspect Celery Queue Backlog
```bash
docker exec -it verism_redis redis-cli -a secure_redis_pass_2026 llen celery
```

### Monitor Live Container Logs
```bash
docker compose logs -f --tail=100 backend celery_worker
```

### Clear Stale Redis Analytics Caches Manually
```bash
docker exec -it verism_redis redis-cli -a secure_redis_pass_2026 --scan --pattern "analytics:*" | xargs -r docker exec -i verism_redis redis-cli -a secure_redis_pass_2026 del
```
