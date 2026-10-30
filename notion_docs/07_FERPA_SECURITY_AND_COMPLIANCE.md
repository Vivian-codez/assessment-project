# 🛡️ 07. FERPA Security & Compliance

> 📌 **Parent Page:** [00. Notion Workspace Hub](file:///c:/Users/alice/OneDrive/Desktop/Prototype/notion_docs/00_NOTION_WORKSPACE_HUB.md)  
> 🏷️ **Status:** 🛡️ Audited & Enforced  
> 📅 **Last Updated:** 2026-10-29  

---

## 🏛️ Regulatory Context: FERPA & GDPR in EdTech

The **Family Educational Rights and Privacy Act (FERPA)** (34 CFR Part 99) mandates that educational institutions strictly control access to student education records, prohibiting the disclosure of Personally Identifiable Information (PII) without prior written consent.

When educational institutions utilize generative AI technologies, common violations occur if:
- Student names, student identification numbers, or emails are ingested into external AI models.
- Commercial LLM providers retain submission text for model fine-tuning or training datasets.
- Student work is unencrypted at rest or exposed across multi-tenant databases.

Verism AI was built from the ground up to **prevent these failure modes entirely**.

---

## 🔒 3-Layer Privacy Shield Architecture

```
                               RAW STUDENT SUBMISSION
                         ("Jane Doe", ID #88412, Math Essay)
                                       │
                                       ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │ LAYER 1: Transparent Field-Level Encryption at Rest (Fernet AES-128) │
    │ Database stores ciphertext: gAAAAABl... (keys kept outside DB)       │
    └──────────────────────────────────┬───────────────────────────────────┘
                                       │
                                       ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │ LAYER 2: Deterministic In-Memory Pseudonymization                    │
    │ "Jane Doe" ─────────────► [STUDENT_TOKEN_9A3F]                       │
    │ "88412"    ─────────────► [ROLL_TOKEN_C41D]                          │
    └──────────────────────────────────┬───────────────────────────────────┘
                                       │
                                       ▼
    ┌──────────────────────────────────────────────────────────────────────┐
    │ LAYER 3: Zero-Data-Retention LLM Transmission                        │
    │ Transmit ONLY sanitized text to Google Gemini inference endpoints.   │
    │ Zero PII reaches Google servers. Results linked back locally.        │
    └──────────────────────────────────────────────────────────────────────┘
```

---

## 🔐 1. Cryptographic Encryption at Rest (Fernet AES-128)

Implemented in `backend/app/core/security.py`:
- Employs **Fernet cryptography** (symmetric AES-128 in Cipher Block Chaining [CBC] mode, authenticated using HMAC with SHA-256).
- Student PII attributes (`student_name_encrypted`, `student_roll_encrypted`, `student_email_encrypted`) are encrypted *before* the SQL `INSERT` statement executes.
- **Key Isolation**: The encryption key is loaded from an isolated environment variable (`FERPA_ENCRYPTION_KEY`) and is never written into the database itself.

---

## 🎭 2. In-Memory Pseudonymization Pipeline

Before any submission content or essay text is packaged into prompt payloads for Google Gemini:
1. The submission text is scanned for student names, roll numbers, and emails using the student's roster metadata.
2. Every occurrence is replaced with an opaque cryptographic token:
   ```
   Original: "Submitted by Alice Walker, Student ID: 2024-CS-091"
   Masked:   "Submitted by [STUDENT_NAME], Student ID: [STUDENT_ROLL]"
   ```
3. Gemini processes the paper, scoring criteria objectively without knowing the student's demographic identity.
4. When the structured grading output returns to FastAPI, the backend maps the draft grade back to the database record using the internal database primary key.

---

## 📜 3. Immutable Compliance Audit Logging

Every sensitive operation is logged to the `audit_logs` table:

```sql
CREATE TABLE public.audit_logs (
    id VARCHAR(64) PRIMARY KEY,
    instructor_id VARCHAR(64) REFERENCES instructors(id),
    action VARCHAR(64) NOT NULL, -- 'GRADE_STAMP', 'GRADE_OVERRIDE', 'PII_DECRYPT', 'EXPORT_CSV'
    target_entity VARCHAR(64) NOT NULL,
    target_id VARCHAR(64) NOT NULL,
    changes JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### Logged Operations:
- **`GRADE_STAMP`**: Records timestamp, instructor ID, final score, and rubric values when a teacher stamps approval.
- **`GRADE_OVERRIDE`**: Captures original AI score vs. teacher-adjusted score with instructor's justification comment.
- **`PII_DECRYPT`**: Audit record created whenever student names are unmasked for gradebook export.
- **`FLAG_DISMISSAL`**: Records instructor reasoning if a plagiarism alert is dismissed as benign.

---

## ✅ FERPA Compliance Verification Checklist

- [x] **Zero PII to LLMs**: Student identifiers stripped before external network transmission.
- [x] **Encrypted at Rest**: All student names and roll numbers stored as ciphertext.
- [x] **Zero Model Training**: Configured with enterprise API parameters ensuring student work is never used to train or improve models.
- [x] **Human Review Mandate**: AI does not make unilateral grade determinations.
- [x] **Role-Based Access**: Instructors can only view rosters and submissions for courses they own.
- [x] **Right to Rectification**: Instructors have absolute override authority over all points and criteria feedback.
