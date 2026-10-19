"""Supabase Database Service Layer.

Interacts directly with Supabase via `supabase-py` and PostgREST client:
- Tables: Courses, Instructors, Submissions, Rubrics, Draft Grades, Audit Logs
- Includes transparent FERPA/GDPR encryption handlers
- Provides graceful local fallback when Supabase connection is offline
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.core.supabase import supabase
from app.core.logging import logger
from app.core.security import ferpa_cipher
from app.core.database import SessionLocal
from app.models.course import Course
from app.models.instructor import Instructor
from app.models.submission import Submission
from app.models.rubric import Rubric, RubricCriterion
from app.models.draft_grade import DraftGrade
from app.models.audit_log import AuditLog
from app.models.similarity_match import SimilarityMatch


class SupabaseService:
    """Direct PostgREST database layer using supabase-py."""

    def __init__(self):
        self.client = supabase

    # ==========================================
    # Courses
    # ==========================================
    def get_courses(self, search: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query courses table via PostgREST: supabase.table("courses").select("*")."""
        try:
            query = self.client.table("courses").select("*")
            if search:
                query = query.ilike("name", f"%{search}%")
            response = query.execute()
            if response.data:
                return response.data
        except Exception as e:
            logger.warning(f"Supabase PostgREST query on 'courses' fallback: {e}")

        # Local fallback
        db = SessionLocal()
        try:
            q = db.query(Course)
            if search:
                pattern = f"%{search}%"
                q = q.filter(Course.name.ilike(pattern) | Course.code.ilike(pattern))
            items = q.all()
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "code": c.code,
                    "section": c.section,
                    "tone": c.tone,
                    "students_count": c.students_count,
                    "instructor_id": c.instructor_id,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in items
            ]
        finally:
            db.close()

    def get_course_by_id(self, course_id: str) -> Optional[Dict[str, Any]]:
        """Fetch course by ID."""
        try:
            res = self.client.table("courses").select("*").eq("id", course_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase query error: {e}")

        db = SessionLocal()
        try:
            c = db.query(Course).filter(Course.id == course_id).first()
            if c:
                return {
                    "id": c.id,
                    "name": c.name,
                    "code": c.code,
                    "section": c.section,
                    "tone": c.tone,
                    "students_count": c.students_count,
                    "instructor_id": c.instructor_id,
                }
            return None
        finally:
            db.close()

    # ==========================================
    # Instructors
    # ==========================================
    def get_instructor_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Query instructors table via PostgREST: supabase.table("instructors")."""
        try:
            res = self.client.table("instructors").select("*").eq("email", email).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase PostgREST query on 'instructors' fallback: {e}")

        db = SessionLocal()
        try:
            inst = db.query(Instructor).filter(Instructor.email == email).first()
            if inst:
                return {
                    "id": inst.id,
                    "name": inst.name,
                    "email": inst.email,
                    "role": inst.role,
                    "hashed_password": inst.hashed_password,
                    "preferences": inst.preferences or {},
                }
            return None
        finally:
            db.close()

    # ==========================================
    # Submissions (with FERPA Encryption Handlers)
    # ==========================================
    def get_submissions(self, assignment_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Query submissions table via PostgREST with FERPA decryption."""
        try:
            query = self.client.table("submissions").select("*").eq("assignment_id", assignment_id)
            if status:
                query = query.eq("status", status)
            res = query.execute()
            if res.data:
                results = []
                for row in res.data:
                    # Decrypt FERPA fields
                    row["student_name"] = ferpa_cipher.decrypt(row.get("student_name_encrypted", "")) or "Student"
                    row["student_roll"] = ferpa_cipher.decrypt(row.get("student_roll_encrypted", "")) or ""
                    row["student_email"] = ferpa_cipher.decrypt(row.get("student_email_encrypted", "")) or ""
                    results.append(row)
                return results
        except Exception as e:
            logger.warning(f"Supabase PostgREST query on 'submissions' fallback: {e}")

        db = SessionLocal()
        try:
            q = db.query(Submission).filter(Submission.assignment_id == assignment_id)
            if status:
                q = q.filter(Submission.status == status)
            subs = q.all()
            return [
                {
                    "id": s.id,
                    "assignment_id": s.assignment_id,
                    "student_name": s.student_name,
                    "student_roll": s.student_roll,
                    "student_email": s.student_email,
                    "file_name": s.file_name,
                    "file_path": s.file_path,
                    "extracted_text": s.extracted_text,
                    "similarity_score": s.similarity_score,
                    "ai_content_probability": s.ai_content_probability,
                    "status": s.status,
                    "created_at": s.created_at.isoformat() if s.created_at else None,
                }
                for s in subs
            ]
        finally:
            db.close()

    def get_submission_by_id(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Fetch single submission with decrypted student info."""
        try:
            res = self.client.table("submissions").select("*").eq("id", submission_id).execute()
            if res.data:
                row = res.data[0]
                row["student_name"] = ferpa_cipher.decrypt(row.get("student_name_encrypted", "")) or "Student"
                row["student_roll"] = ferpa_cipher.decrypt(row.get("student_roll_encrypted", "")) or ""
                row["student_email"] = ferpa_cipher.decrypt(row.get("student_email_encrypted", "")) or ""
                return row
        except Exception as e:
            logger.warning(f"Supabase PostgREST get_submission error: {e}")

        db = SessionLocal()
        try:
            s = db.query(Submission).filter(Submission.id == submission_id).first()
            if s:
                return {
                    "id": s.id,
                    "assignment_id": s.assignment_id,
                    "student_name": s.student_name,
                    "student_roll": s.student_roll,
                    "student_email": s.student_email,
                    "file_name": s.file_name,
                    "file_path": s.file_path,
                    "extracted_text": s.extracted_text,
                    "similarity_score": s.similarity_score,
                    "ai_content_probability": s.ai_content_probability,
                    "status": s.status,
                }
            return None
        finally:
            db.close()

    # ==========================================
    # Supabase Storage Integration
    # ==========================================
    def upload_file_to_storage(
        self,
        file_bytes: bytes,
        file_name: str,
        assignment_id: str,
        content_type: Optional[str] = None,
    ) -> Optional[str]:
        """Uploads raw student submission file (.docx, .pdf, .txt, etc.) directly

        into Supabase Storage bucket 'submissions', generating and returning its public URL.
        """
        if not self.client:
            logger.warning("Supabase client offline; skipping storage upload.")
            return None

        try:
            import mimetypes
            clean_name = os.path.basename(file_name)
            ext = clean_name.lower().split(".")[-1] if "." in clean_name else ""
            if not content_type:
                content_type, _ = mimetypes.guess_type(clean_name)
                if not content_type:
                    if ext == "docx":
                        content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    elif ext == "pdf":
                        content_type = "application/pdf"
                    elif ext in {"txt", "py", "js", "ts", "html", "css", "md"}:
                        content_type = "text/plain"
                    else:
                        content_type = "application/octet-stream"

            storage_path = f"{assignment_id}/{uuid.uuid4().hex[:8]}_{clean_name}"
            # Ensure bucket exists or proceed with upload
            self.client.storage.from_("submissions").upload(
                path=storage_path,
                file=file_bytes,
                file_options={"content-type": content_type, "upsert": "true"},
            )
            public_url = self.client.storage.from_("submissions").get_public_url(storage_path)
            logger.info(f"Uploaded file {file_name} to Supabase Storage at {storage_path}. Public URL: {public_url}")
            return public_url
        except Exception as e:
            logger.warning(f"Supabase Storage upload warning for {file_name}: {e}")
            return None

    def create_submission(
        self,
        assignment_id: str,
        student_name: str,
        student_roll: str,
        file_name: str,
        file_path: Optional[str] = None,
        extracted_text: Optional[str] = None,
        student_email: Optional[str] = None,
        file_url: Optional[str] = None,
        content: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a student submission encrypting student PII before writing."""
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        enc_name = ferpa_cipher.encrypt(student_name)
        enc_roll = ferpa_cipher.encrypt(student_roll)
        enc_email = ferpa_cipher.encrypt(student_email) if student_email else None

        stored_content = content or extracted_text or ""
        payload = {
            "id": sub_id,
            "assignment_id": assignment_id,
            "student_name_encrypted": enc_name,
            "student_roll_encrypted": enc_roll,
            "student_email_encrypted": enc_email,
            "file_name": file_name,
            "file_path": file_path,
            "file_url": file_url,
            "extracted_text": extracted_text,
            "content": stored_content,
            "status": "pending",
            "similarity_score": 0.0,
            "ai_content_probability": 0.0,
            "web_plagiarism_score": 0.0,
            "web_sources": [],
        }

        try:
            res = self.client.table("submissions").insert(payload).execute()
            if res.data:
                row = res.data[0]
                row["student_name"] = student_name
                row["student_roll"] = student_roll
                return row
        except Exception as e:
            logger.warning(f"Supabase PostgREST insert 'submissions' fallback: {e}")
            err_str = str(e).lower()
            if "assignment_id_fkey" in err_str or "foreign key" in err_str:
                try:
                    ldb = SessionLocal()
                    from app.models.assignment import Assignment
                    local_assign = ldb.query(Assignment).filter(Assignment.id == assignment_id).first()
                    local_course = ldb.query(Course).first()
                    ldb.close()
                    course_id = local_assign.course_id if local_assign else (local_course.id if local_course else "c_cs201")
                    self.client.table("courses").upsert({
                        "id": course_id,
                        "name": local_course.name if local_course else "Data Structures",
                        "code": local_course.code if local_course else "CS201",
                        "section": "A",
                    }).execute()
                    self.client.table("assignments").upsert({
                        "id": assignment_id,
                        "course_id": course_id,
                        "title": local_assign.title if local_assign else f"Assignment {assignment_id}",
                        "description": "Active student assignment.",
                        "max_score": 100.0,
                    }).execute()
                    retry_res = self.client.table("submissions").insert(payload).execute()
                    if retry_res.data:
                        row = retry_res.data[0]
                        row["student_name"] = student_name
                        row["student_roll"] = student_roll
                        return row
                except Exception as retry_err:
                    logger.warning(f"Supabase submission retry notice: {retry_err}")

        db = SessionLocal()
        try:
            sub = Submission(
                id=sub_id,
                assignment_id=assignment_id,
                student_name_encrypted=enc_name,
                student_roll_encrypted=enc_roll,
                student_email_encrypted=enc_email,
                file_name=file_name,
                file_path=file_path,
                file_url=file_url,
                extracted_text=extracted_text,
                content=stored_content,
                file_content=stored_content,
                status="pending",
                similarity_score=0.0,
                ai_content_probability=0.0,
                web_plagiarism_score=0.0,
                web_sources=[],
            )
            db.add(sub)
            db.commit()
            return payload
        finally:
            db.close()

    def get_peer_submissions(
        self,
        assignment_id: str,
        exclude_submission_id: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Fetch all peer submissions for cross-similarity auditing from Supabase."""
        try:
            query = self.client.table("submissions").select("*").eq("assignment_id", assignment_id)
            if exclude_submission_id:
                query = query.neq("id", exclude_submission_id)
            res = query.execute()
            if res.data:
                peers = []
                for row in res.data:
                    row["student_name"] = ferpa_cipher.decrypt(row.get("student_name_encrypted", "")) or "Peer"
                    row["student_roll"] = ferpa_cipher.decrypt(row.get("student_roll_encrypted", "")) or ""
                    peers.append(row)
                return peers
        except Exception as e:
            logger.warning(f"Supabase peer submissions query error: {e}")

        # Local fallback
        db = SessionLocal()
        try:
            q = db.query(Submission).filter(Submission.assignment_id == assignment_id)
            if exclude_submission_id:
                q = q.filter(Submission.id != exclude_submission_id)
            subs = q.all()
            return [
                {
                    "id": s.id,
                    "assignment_id": s.assignment_id,
                    "student_name": s.student_name,
                    "student_roll": s.student_roll,
                    "extracted_text": s.extracted_text or s.file_content or "",
                    "file_name": s.file_name,
                }
                for s in subs
            ]
        finally:
            db.close()

    def get_assignment_details(self, assignment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch assignment along with rubric criteria and reference exemplar."""
        try:
            res = self.client.table("assignments").select("*").eq("id", assignment_id).execute()
            if res.data:
                assignment = res.data[0]
                rubric_id = assignment.get("rubric_id")
                if rubric_id:
                    rubric = self.get_rubric(rubric_id)
                    assignment["rubric"] = rubric
                return assignment
        except Exception as e:
            logger.warning(f"Supabase assignment lookup notice: {e}")

        db = SessionLocal()
        try:
            a = db.query(Assignment).filter(Assignment.id == assignment_id).first()
            if a:
                return {
                    "id": a.id,
                    "course_id": a.course_id,
                    "title": a.title,
                    "description": a.description,
                    "max_score": a.max_score,
                    "rubric_id": a.rubric_id,
                    "reference_assignment_text": a.reference_assignment_text,
                }
            return None
        finally:
            db.close()

    def save_evaluation_results(
        self,
        submission_id: str,
        overall_score: float,
        similarity_score: float,
        ai_content_probability: float,
        web_plagiarism_score: float,
        web_sources: List[Dict[str, Any]],
        criteria_scores: List[Dict[str, Any]],
        ai_feedback: str,
        is_flagged: bool,
    ) -> bool:
        """Update submission record in Supabase with parsed scores, feedback, flags, and audit payload."""
        status = "flagged" if is_flagged else "graded"
        # 1. Update submissions table
        try:
            sub_update = {
                "similarity_score": similarity_score,
                "ai_content_probability": ai_content_probability,
                "web_plagiarism_score": web_plagiarism_score,
                "web_sources": web_sources,
                "status": status,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            self.client.table("submissions").update(sub_update).eq("id", submission_id).execute()
        except Exception as e:
            logger.error(f"Failed to update submission {submission_id} in Supabase: {e}")

        # 2. Upsert draft_grades table
        try:
            draft_id = f"draft_{submission_id}"
            draft_payload = {
                "id": draft_id,
                "submission_id": submission_id,
                "suggested_score": overall_score,
                "criteria_scores": criteria_scores,
                "ai_feedback": ai_feedback,
                "status": "flagged" if is_flagged else "pending",
                "ai_model": settings.GEMINI_MODEL,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            self.client.table("draft_grades").upsert(draft_payload).execute()
        except Exception as e:
            logger.error(f"Failed to upsert draft grade for {submission_id} in Supabase: {e}")

        return True
    # ==========================================
    def get_rubric(self, rubric_id: str) -> Optional[Dict[str, Any]]:
        """Query rubrics table via PostgREST: supabase.table("rubrics")."""
        try:
            res = self.client.table("rubrics").select("*, criteria:rubric_criteria(*)").eq("id", rubric_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase PostgREST query on 'rubrics' fallback: {e}")

        db = SessionLocal()
        try:
            r = db.query(Rubric).filter(Rubric.id == rubric_id).first()
            if r:
                return {
                    "id": r.id,
                    "name": r.name,
                    "course_id": r.course_id,
                    "total_max_score": r.total_max_score,
                    "criteria": [
                        {
                            "id": c.id,
                            "name": c.name,
                            "description": c.description,
                            "weight": c.weight,
                            "max_score": c.max_score,
                            "order_index": c.order_index,
                        }
                        for c in r.criteria
                    ],
                }
            return None
        finally:
            db.close()

    # ==========================================
    # Draft Grades
    # ==========================================
    def get_draft_grade(self, submission_id: str) -> Optional[Dict[str, Any]]:
        """Query draft_grades table via PostgREST: supabase.table("draft_grades")."""
        try:
            res = self.client.table("draft_grades").select("*").eq("submission_id", submission_id).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase PostgREST query on 'draft_grades' fallback: {e}")

        db = SessionLocal()
        try:
            dg = db.query(DraftGrade).filter(DraftGrade.submission_id == submission_id).first()
            if dg:
                return {
                    "id": dg.id,
                    "submission_id": dg.submission_id,
                    "suggested_score": dg.suggested_score,
                    "final_score": dg.final_score,
                    "criteria_scores": dg.criteria_scores,
                    "ai_feedback": dg.ai_feedback,
                    "teacher_feedback": dg.teacher_feedback,
                    "status": dg.status,
                    "ai_model": dg.ai_model,
                    "approved_at": dg.approved_at.isoformat() if dg.approved_at else None,
                }
            return None
        finally:
            db.close()

    def upsert_draft_grade(self, draft_data: Dict[str, Any]) -> Dict[str, Any]:
        """Upsert draft grade directly to Supabase."""
        try:
            res = self.client.table("draft_grades").upsert(draft_data).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase PostgREST upsert 'draft_grades' fallback: {e}")

        db = SessionLocal()
        try:
            sub_id = draft_data["submission_id"]
            existing = db.query(DraftGrade).filter(DraftGrade.submission_id == sub_id).first()
            if existing:
                for k, v in draft_data.items():
                    if hasattr(existing, k) and k != "id":
                        setattr(existing, k, v)
            else:
                new_draft = DraftGrade(**draft_data)
                db.add(new_draft)
            db.commit()
            return draft_data
        finally:
            db.close()

    # ==========================================
    # Audit Logs
    # ==========================================
    def log_audit(
        self,
        actor_name: str,
        action: str,
        entity_type: str,
        entity_id: str,
        details: Optional[Dict[str, Any]] = None,
        actor_id: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Record audit log directly via PostgREST: supabase.table("audit_logs")."""
        log_id = f"audit_{uuid.uuid4().hex[:12]}"
        payload = {
            "id": log_id,
            "actor_id": actor_id,
            "actor_name": actor_name,
            "action": action,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "details": details or {},
            "ip_address": ip_address,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        try:
            res = self.client.table("audit_logs").insert(payload).execute()
            if res.data:
                return res.data[0]
        except Exception as e:
            logger.warning(f"Supabase PostgREST insert 'audit_logs' fallback: {e}")

        db = SessionLocal()
        try:
            log_record = AuditLog(
                id=log_id,
                actor_id=actor_id,
                actor_name=actor_name,
                action=action,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details or {},
                ip_address=ip_address,
            )
            db.add(log_record)
            db.commit()
            return payload
        finally:
            db.close()


supabase_service = SupabaseService()
