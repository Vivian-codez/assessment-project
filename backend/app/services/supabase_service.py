"""Supabase Database Service Layer.

Interacts directly with Supabase via `supabase-py` and PostgREST client:
- Tables: Courses, Instructors, Submissions, Rubrics, Draft Grades, Audit Logs
- Includes transparent FERPA/GDPR encryption handlers
- Provides graceful local fallback when Supabase connection is offline
"""

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

    def create_submission(
        self,
        assignment_id: str,
        student_name: str,
        student_roll: str,
        file_name: str,
        file_path: Optional[str] = None,
        extracted_text: Optional[str] = None,
        student_email: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Creates a student submission encrypting student PII before writing."""
        sub_id = f"sub_{uuid.uuid4().hex[:12]}"
        enc_name = ferpa_cipher.encrypt(student_name)
        enc_roll = ferpa_cipher.encrypt(student_roll)
        enc_email = ferpa_cipher.encrypt(student_email) if student_email else None

        payload = {
            "id": sub_id,
            "assignment_id": assignment_id,
            "student_name_encrypted": enc_name,
            "student_roll_encrypted": enc_roll,
            "student_email_encrypted": enc_email,
            "file_name": file_name,
            "file_path": file_path,
            "extracted_text": extracted_text,
            "status": "pending",
            "similarity_score": 0.0,
            "ai_content_probability": 0.0,
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
                extracted_text=extracted_text,
                status="pending",
                similarity_score=0.0,
                ai_content_probability=0.0,
            )
            db.add(sub)
            db.commit()
            return payload
        finally:
            db.close()

    # ==========================================
    # Rubrics
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
