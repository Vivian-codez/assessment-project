# Verism AI — Editorial & Copywriting Guide

## 1. Brand Voice & Guiding Tenet
Verism AI is an instrument designed for rigorous, thoughtful educators. The voice is:
- **Honest:** We never exaggerate capabilities, fabricate percentages, or promise compliance badges we have not verified.
- **Respectful of Teacher Agency:** The AI is an assistant that drafts suggestions. The teacher is the final, accountable judge.
- **Direct & Action-Oriented:** Interface labels describe the concrete outcome of an action, not generic verbs.

### The Motto
> **"AI suggests. You stamp. Every grade waits for your approval. Grading never starts without your command."**

---

## 2. Canonical Terminology

| Correct Term | Deprecated / Disallowed Term | Context / Rationale |
|---|---|---|
| **Roll call / Student Roster** | User database / Lead list | Standard academic vocabulary for class attendance & enrollment |
| **Peer Similarity / Collision** | 3-Way Plagiarism / Definite Cheating | Winnowing algorithm measures textual & structural token overlap, not human moral intent |
| **AI Content Likelihood** | AI Detector / 100% AI Guaranteed | Statistical likelihood indicators are probabilistic signals, never definitive proof |
| **Web Citations** | Public Web Plagiarism Audit | External sources and literature cross-references; explicit note when external provider not configured |
| **Student Pseudonymization** | FERPA-Grade AES-256 Vault | Real implementation: Fernet field encryption at rest + deterministic token substitution before LLM |
| **Stamp Grade / Approve** | Submit / Finalize / Accept | Explicit metaphor reflecting teacher authoritative stamp of approval |
| **Start Grading** | Auto-grade on upload | Grading is explicitly initiated by the teacher and never automatically on file drop |
| **Reference Solution / Exemplar** | Golden Solution / Key | Pedagogical reference standard against which student submissions are benchmarked |

---

## 3. Outcome-Based Button & Action Labels

Avoid vague one-word actions. Prefer descriptive, outcome-oriented button labels:

| Context | Recommended Label | Avoid |
|---|---|---|
| Roster export | `Export roll call (CSV)` | `Export`, `Download` |
| Roster import | `Import roll call` | `Upload`, `Import` |
| Manual enrollment | `Add students manually` | `Add`, `Create` |
| Batch grading trigger | `Start Grading (Pre-flight)` | `Run`, `Go`, `Submit` |
| Grade approval | `Approve & Stamp Grade` | `OK`, `Save`, `Approve` |
| Grade adjustment | `Override Score` | `Edit`, `Change` |

---

## 4. Honest Placeholders & Unanalyzed States

**Strict Rule:** No scores, percentages, or status badges may be shown until an analysis has actually been executed.
- If a submission has not been graded: show `"—"`, never `"0%"` or `"0/100"`.
- If an assignment has no submissions: KPI displays `"—"`, subtitle reads `"No submissions received yet"`.
- If similarity checks have not run: show `"—"`.
- If public web search is not configured: display `"Public web search not configured (local/peer comparison active)"` instead of `"0% Web Plagiarism"`.

---

## 5. Pluralization & Grammatical Precision

Always use the pluralization helper `pluralize(count, singular, plural)`:
- `0 submissions`, `1 submission`, `14 submissions`
- `0 students`, `1 student`, `38 students`
- `0 criteria`, `1 criterion`, `5 criteria`
- `0 rubrics`, `1 rubric`, `4 rubrics`

Never render naive patterns like `1 submission(s)` or `Student(s)`.

---

## 6. Error Messages & Toasts

All error messages must provide actionable clarity following this pattern:
`[What failed] + [Exact server reason] + [Next step / remedy]`

### Examples:
- **CSV Import Header Error:**
  *"Could not import roll call. No valid rows detected. Missing required column 'roll_number'. Detected headers: 'ID', 'Student Name'. Download sample template to verify structure."*
- **Grading Inactive Rubric Error:**
  *"Cannot start grading. Assignment 'Midterm Exam' does not have an active rubric assigned. Please configure criteria in Rubrics tab before starting."*
- **Network / Supabase Timeout:**
  *"Database connection timed out while saving grade history. Your changes are saved locally. Click 'Retry' to synchronize."*
