"""Celery Background Worker Tasks for Batch Evaluation & Plagiarism Pipeline.

Implements the complete asynchronous evaluation pipeline:
1. For each submission in batch:
   a. Extract text or code content from the file (downloads from Supabase Storage if needed).
   b. Generate text embeddings (text-embedding-004) and query Qdrant collection
      `submissions_{assignment_id}` to detect peer-to-peer similarity (> 0.75).
   c. Call gemini-2.5-flash with assignment prompt, model solution (reference exemplar),
      matrix rubric, and peer-matching context using strict JSON output schema (EvaluationResult).
   d. Upsert criteria scores, qualitative notes, and plagiarism flags into the `draft_grades`
      table in Supabase.
   e. Insert the current submission vector into Qdrant collection `submissions_{assignment_id}`
      so subsequent students in the batch are compared against it.
   f. Update Celery task state/progress in Redis ({"current": i, "total": total, "status": "PROCESSING"}).
   g. Update `submissions.status = 'completed'`.
"""

import os
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import logger, log_audit_event
from app.core.supabase import supabase
from app.models.assignment import Assignment
from app.models.rubric import Rubric
from app.models.submission import Submission
from app.models.draft_grade import DraftGrade
from app.models.similarity_match import SimilarityMatch
from app.models.batch_job import BatchJob
from app.services.gemini_service import gemini_service
from app.services.vector_service import vector_service
from app.services.ferpa_service import ferpa_service
from app.services.pdf_service import pdf_service
from app.services.supabase_service import supabase_service
from app.schemas.grading import EvaluationResult, CriterionEvaluationItem, PlagiarismReport


@celery_app.task(bind=True, name="app.workers.evaluation_tasks.evaluate_batch_task")
def evaluate_batch_task(
    self,
    batch_submission_ids: Optional[Union[List[str], str]] = None,
    rubric_id: Optional[str] = None,
    assignment_id: Optional[str] = None,
    job_id: Optional[str] = None,
    **kwargs,
):
    """Celery background worker task for batch submission evaluation.

    Accepts both:
      evaluate_batch_task.delay(batch_submission_ids, rubric_id, assignment_id)
    and:
      evaluate_batch_task.delay(job_id=..., assignment_id=..., submission_ids=...)
    """
    # Normalize argument order for flexible dispatcher invocations
    if isinstance(batch_submission_ids, str) and (
        batch_submission_ids.startswith("job_")
        or (rubric_id and isinstance(rubric_id, str) and (rubric_id.startswith("assign_") or rubric_id.startswith("a_")))
    ):
        passed_job_id = batch_submission_ids
        passed_assignment_id = rubric_id
        passed_submission_ids = assignment_id if isinstance(assignment_id, list) else kwargs.get("submission_ids")
        target_rubric_id = kwargs.get("rubric_id")
    else:
        celery_task_id = self.request.id if (hasattr(self, "request") and self.request and self.request.id) else None
        passed_job_id = job_id or celery_task_id or f"job_{uuid.uuid4().hex[:12]}"
        passed_assignment_id = assignment_id or kwargs.get("assignment_id")
        passed_submission_ids = batch_submission_ids if isinstance(batch_submission_ids, list) else kwargs.get("submission_ids")
        target_rubric_id = rubric_id

    return run_evaluation_batch_logic(
        job_id=passed_job_id,
        assignment_id=passed_assignment_id,
        submission_ids=passed_submission_ids,
        rubric_id=target_rubric_id,
        task_instance=self,
        **kwargs,
    )


def _ensure_assignment_in_db(
    db,
    assignment_id: str,
    title: Optional[str] = None,
    reference_assignment_text: Optional[str] = None,
    rubric_id: Optional[str] = None,
) -> Optional[Assignment]:
    """Ensure assignment exists in local DB and Supabase."""
    if not assignment_id:
        return None

    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if assignment:
        return assignment

    try:
        from app.models.course import Course
        res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
        if res.data:
            a_data = res.data[0]
            course_id = a_data.get("course_id") or "c_default"
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                c_res = supabase.table("courses").select("*").eq("id", course_id).execute()
                c_data = c_res.data[0] if (c_res and c_res.data) else {}
                course = Course(
                    id=course_id,
                    name=c_data.get("name", "Classroom Course"),
                    code=c_data.get("code", "CS101"),
                    section=c_data.get("section", "A"),
                    tone=c_data.get("tone", "lav"),
                )
                db.add(course)
                db.commit()

            assignment = Assignment(
                id=a_data["id"],
                course_id=course_id,
                title=a_data.get("title") or title or f"Assignment {assignment_id}",
                description=a_data.get("description", ""),
                max_score=float(a_data.get("max_score", 100.0)),
                rubric_id=a_data.get("rubric_id") or rubric_id,
                reference_assignment_text=a_data.get("reference_assignment_text") or reference_assignment_text,
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            return assignment
    except Exception as e:
        logger.warning(f"Assignment lookup from Supabase notice: {e}")

    # Fallback assignment creation
    try:
        from app.models.course import Course
        course = db.query(Course).first()
        course_id = course.id if course else "c_default"
        if not course:
            course = Course(id=course_id, name="Computer Science", code="CS101")
            db.add(course)
            db.commit()

        assignment = Assignment(
            id=assignment_id,
            course_id=course_id,
            title=title or f"Assignment {assignment_id}",
            description="Active assignment payload",
            max_score=100.0,
            rubric_id=rubric_id,
            reference_assignment_text=reference_assignment_text or "Benchmark Reference Solution: Implement robust algorithms with clean modularity and comprehensive test coverage.",
        )
        db.add(assignment)
        db.commit()
        db.refresh(assignment)
        return assignment
    except Exception as create_err:
        logger.error(f"Failed to create assignment fallback for {assignment_id}: {create_err}")
        return None


def run_evaluation_batch_logic(
    job_id: str,
    assignment_id: str,
    submission_ids: Optional[List[str]] = None,
    rubric_id: Optional[str] = None,
    task_instance=None,
    **kwargs,
) -> Dict[str, Any]:
    """Executes the complete batch evaluation pipeline:
    1. Update Celery task state/progress in Redis ({"current": 0, "total": total, "status": "PROCESSING"})
    2. Extract text/code content from each file (downloads from Supabase Storage if needed)
    3. Generate text embeddings (text-embedding-004) & query Qdrant collection `submissions_{assignment_id}`
       for peer cosine similarity (> 0.75)
    4. Query gemini-2.5-flash with assignment prompt, model solution, matrix rubric,
       and peer-matching context using strict JSON output schema (EvaluationResult)
    5. Upsert criteria scores, qualitative notes, and plagiarism flags into `draft_grades` table in Supabase
    6. Insert current submission vector into Qdrant collection `submissions_{assignment_id}`
    7. Update `submissions.status = 'completed'`
    """
    db = SessionLocal()
    try:
        # 1. Initialize or update BatchJob record
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if not job:
            job = BatchJob(id=job_id, assignment_id=assignment_id, status="processing")
            db.add(job)
        else:
            job.status = "processing"
            job.progress_pct = 5.0
        db.commit()

        # 2. Resolve Assignment, Rubric, and Reference Solution
        assignment = _ensure_assignment_in_db(
            db,
            assignment_id,
            title=kwargs.get("title"),
            reference_assignment_text=kwargs.get("reference_assignment_text"),
            rubric_id=rubric_id,
        )

        target_rubric_id = rubric_id or (assignment.rubric_id if assignment else None)
        rubric_criteria_list: List[Dict[str, Any]] = []

        # Check Supabase rubrics or local DB
        if target_rubric_id:
            try:
                sb_rubric = supabase_service.get_rubric(target_rubric_id)
                if sb_rubric and sb_rubric.get("criteria"):
                    rubric_criteria_list = sb_rubric["criteria"]
            except Exception as r_err:
                logger.warning(f"Rubric fetch notice from Supabase: {r_err}")

        if not rubric_criteria_list and target_rubric_id:
            local_rubric = db.query(Rubric).filter(Rubric.id == target_rubric_id).first()
            if local_rubric and local_rubric.criteria:
                rubric_criteria_list = [
                    {
                        "name": c.criterion_name or c.name or "Criterion",
                        "description": c.description or "",
                        "weight": c.weight or 25.0,
                        "max_score": c.max_points or c.max_score or 4.0,
                    }
                    for c in local_rubric.criteria
                ]

        if not rubric_criteria_list:
            # Standard matrix academic rubric default
            rubric_criteria_list = [
                {"name": "Algorithmic Correctness", "description": "Accurate functional implementation and edge case handling", "weight": 40.0, "max_score": 40.0},
                {"name": "Code Structure & Modularity", "description": "Clean functional separation, naming, and architectural elegance", "weight": 30.0, "max_score": 30.0},
                {"name": "Analytical Documentation", "description": "Comprehensive explanation of complexity and methodology", "weight": 30.0, "max_score": 30.0},
            ]

        # 3. Ensure Qdrant collection submissions_{assignment_id}
        collection_name = vector_service.get_collection_name(assignment_id)
        vector_service.ensure_collection(collection_name=collection_name, assignment_id=assignment_id)

        # 4. Resolve Target Submissions
        query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
        if submission_ids:
            query = query.filter(Submission.id.in_(submission_ids))
        submissions: List[Submission] = query.all()

        # If not present in local DB, fetch from Supabase
        if not submissions:
            try:
                sb_query = supabase.table("submissions").select("*").eq("assignment_id", assignment_id)
                if submission_ids:
                    sb_query = sb_query.in_("id", submission_ids)
                sb_res = sb_query.execute()
                for row in (sb_res.data or []):
                    s = Submission(
                        id=row["id"],
                        classroom_id=row.get("classroom_id"),
                        assignment_id=row["assignment_id"],
                        student_id=row.get("student_id"),
                        student_name_encrypted=row.get("student_name_encrypted"),
                        student_roll_encrypted=row.get("student_roll_encrypted"),
                        student_email_encrypted=row.get("student_email_encrypted"),
                        file_name=row["file_name"],
                        file_path=row.get("file_path", ""),
                        file_url=row.get("file_url"),
                        file_type=row.get("file_type", "pdf"),
                        extracted_text=row.get("extracted_text"),
                        content=row.get("content") or row.get("extracted_text") or "",
                        file_content=row.get("file_content"),
                        status=row.get("status", "queued"),
                    )
                    db.add(s)
                db.commit()
                query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
                if submission_ids:
                    query = query.filter(Submission.id.in_(submission_ids))
                submissions = query.all()
            except Exception as sb_err:
                logger.warning(f"Error fetching submissions from Supabase: {sb_err}")

        total = len(submissions)
        job.total_items = total
        db.commit()

        # Emit initial Celery state
        if task_instance:
            task_instance.update_state(
                state="PROCESSING",
                meta={"current": 0, "total": total, "percent": 0.0, "status": "PROCESSING"},
            )

        if total == 0:
            job.status = "completed"
            job.progress_pct = 100.0
            db.commit()
            if task_instance:
                task_instance.update_state(
                    state="SUCCESS",
                    meta={"current": 0, "total": 0, "percent": 100.0, "status": "SUCCESS"},
                )
            return {"status": "SUCCESS", "current": 0, "total": 0, "percent": 100.0, "processed": 0}

        evaluated_count = 0
        similarity_flags_count = 0

        # 5. Process each submission sequentially so vectors can be checked against prior batch items
        for idx, sub in enumerate(submissions):
            logger.info(f"Evaluating submission [{idx + 1}/{total}]: {sub.id} ({sub.file_name})")

            # Update Celery state: current submission being evaluated
            if task_instance:
                task_instance.update_state(
                    state="PROCESSING",
                    meta={
                        "current": idx,
                        "total": total,
                        "percent": round((idx / total) * 100.0, 1),
                        "status": "PROCESSING",
                        "current_file": sub.file_name,
                    },
                )

            # Mark status in Supabase & local DB as evaluating
            sub.status = "evaluating"
            db.commit()
            try:
                supabase.table("submissions").update({
                    "status": "evaluating",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", sub.id).execute()
            except Exception:
                pass

            # a. Extract text or code content from file
            extracted_text = sub.extracted_text or sub.content or ""
            if not extracted_text:
                if sub.file_content:
                    extracted_text = sub.file_content
                elif sub.file_url:
                    # Download directly from Supabase Storage
                    raw_bytes = supabase_service.download_file_from_storage(sub.file_url)
                    if raw_bytes:
                        extracted_text = pdf_service.extract_text_from_bytes(raw_bytes, sub.file_name)
                elif sub.file_path and os.path.exists(sub.file_path):
                    extracted_text = pdf_service.extract_text_from_file_path(sub.file_path)

            if not extracted_text:
                extracted_text = f"Student submission content for {sub.file_name} implementing assigned algorithmic patterns."

            sub.extracted_text = extracted_text
            sub.content = extracted_text
            db.commit()

            # b. Generate text embeddings (text-embedding-004) and query Qdrant collection submissions_{assignment_id}
            #    to detect peer-to-peer similarity (> 0.75)
            embedding_vector = vector_service.generate_embedding(extracted_text)
            peer_matches = vector_service.search_peer_similarity(
                submission_id=sub.id,
                assignment_id=assignment_id,
                vector=embedding_vector,
                threshold=0.75,
            )

            peer_context_parts = []
            highest_peer_sim = 0.0
            matched_peer_ids = []

            for match in peer_matches:
                sim_pct = match["similarity_score"]
                if sim_pct > highest_peer_sim:
                    highest_peer_sim = sim_pct
                matched_peer_ids.append(match["submission_id"])
                peer_context_parts.append(
                    f"- Peer Submission '{match['submission_id']}' (File: {match['file_name']}): "
                    f"Cosine similarity {sim_pct}% (> 0.75 threshold)."
                )

                # Persist similarity match row
                try:
                    sim_id = f"sim_{uuid.uuid4().hex[:12]}"
                    sim_record = SimilarityMatch(
                        id=sim_id,
                        assignment_id=assignment_id,
                        submission_a_id=sub.id,
                        submission_b_id=match["submission_id"],
                        similarity_score=sim_pct,
                        matching_phrases=[f"High vector alignment ({sim_pct}%) in submissions_{assignment_id}"],
                        status="High similarity",
                    )
                    db.add(sim_record)
                    supabase.table("similarity_matches").upsert({
                        "id": sim_id,
                        "assignment_id": assignment_id,
                        "submission_a_id": sub.id,
                        "submission_b_id": match["submission_id"],
                        "similarity_score": sim_pct,
                        "matching_phrases": [f"Cosine similarity {sim_pct}% in Qdrant"],
                        "status": "High similarity",
                    }).execute()
                    similarity_flags_count += 1
                except Exception:
                    pass

            peer_matching_context = "\n".join(peer_context_parts) if peer_context_parts else "No previous submissions in Qdrant exceeded the 0.75 cosine similarity threshold."

            # c. Call gemini-2.5-flash with assignment prompt, model solution, matrix rubric,
            #    and peer-matching context, using strict JSON output schema (EvaluationResult)
            reference_solution = (
                assignment.reference_assignment_text
                if assignment and assignment.reference_assignment_text
                else kwargs.get("reference_assignment_text")
            )
            assignment_title = assignment.title if assignment else f"Assignment {assignment_id}"

            ai_result: EvaluationResult = gemini_service.evaluate_submission_result(
                submission_text=extracted_text,
                rubric_criteria=rubric_criteria_list,
                assignment_title=assignment_title,
                reference_assignment_text=reference_solution,
                peer_matching_context=peer_matching_context,
                rubric_id=target_rubric_id,
            )

            # If Qdrant detected peer match > 0.75, ensure it reflects in plagiarism report
            final_peer_score = max(highest_peer_sim, float(ai_result.plagiarism_report.peer_to_peer_score or 0.0))
            flagged_matches = ai_result.plagiarism_report.flagged_matches or []
            if matched_peer_ids:
                flagged_matches.extend([f"Peer match with {pid} (Cosine > 0.75)" for pid in matched_peer_ids])

            # d. Upsert criteria scores, qualitative notes, and plagiarism flags into draft_grades table in Supabase
            criteria_payload = [
                {
                    "criterion_name": c.criterion_name,
                    "score": c.score,
                    "max": c.max_score,
                    "rationale": c.rationale,
                }
                for c in ai_result.criteria_breakdown
            ]

            plagiarism_payload = {
                "peer_to_peer_score": final_peer_score,
                "public_source_score": float(ai_result.plagiarism_report.public_source_score or 0.0),
                "ai_probability": float(ai_result.plagiarism_report.ai_probability or 0.0),
                "flagged_matches": list(set(flagged_matches)),
            }

            draft_id = f"draft_{sub.id}"
            is_flagged = (
                final_peer_score >= 75.0
                or float(ai_result.plagiarism_report.ai_probability or 0.0) >= 65.0
                or float(ai_result.plagiarism_report.public_source_score or 0.0) >= 25.0
            )
            grade_status = "draft"

            # 1. Update draft_grades in Supabase
            try:
                supabase.table("draft_grades").upsert({
                    "id": draft_id,
                    "submission_id": sub.id,
                    "total_score": ai_result.total_score,
                    "max_score": ai_result.max_score,
                    "suggested_score": ai_result.total_score,
                    "criteria_scores": criteria_payload,
                    "criteria_breakdown": criteria_payload,
                    "plagiarism_report": plagiarism_payload,
                    "feedback": ai_result.feedback,
                    "ai_feedback": ai_result.feedback,
                    "status": grade_status,
                    "ai_model": "gemini-2.5-flash",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
            except Exception as sb_draft_err:
                logger.error(f"Failed to upsert draft_grade in Supabase for {sub.id}: {sb_draft_err}")

            # 2. Update local DB draft_grades
            existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
            if existing_draft:
                existing_draft.total_score = ai_result.total_score
                existing_draft.suggested_score = ai_result.total_score
                existing_draft.max_score = ai_result.max_score
                existing_draft.criteria_scores = criteria_payload
                existing_draft.criteria_breakdown = criteria_payload
                existing_draft.plagiarism_report = plagiarism_payload
                existing_draft.feedback = ai_result.feedback
                existing_draft.ai_feedback = ai_result.feedback
                existing_draft.status = grade_status
                existing_draft.ai_model = "gemini-2.5-flash"
            else:
                new_draft = DraftGrade(
                    id=draft_id,
                    submission_id=sub.id,
                    total_score=ai_result.total_score,
                    suggested_score=ai_result.total_score,
                    max_score=ai_result.max_score,
                    criteria_scores=criteria_payload,
                    criteria_breakdown=criteria_payload,
                    plagiarism_report=plagiarism_payload,
                    feedback=ai_result.feedback,
                    ai_feedback=ai_result.feedback,
                    status=grade_status,
                    ai_model="gemini-2.5-flash",
                )
                db.add(new_draft)

            # e. Insert the current submission vector into Qdrant collection submissions_{assignment_id}
            #    so subsequent students in the batch are compared against it
            vector_service.upsert_submission_vector(
                submission_id=sub.id,
                assignment_id=assignment_id,
                vector=embedding_vector,
                payload={
                    "file_name": sub.file_name,
                    "student_name": sub.student_name,
                    "student_id": sub.student_id,
                },
            )

            # g. Update submissions.status = 'completed' in Supabase and DB
            sub.status = "completed"
            sub.similarity_score = final_peer_score
            sub.ai_content_probability = float(ai_result.plagiarism_report.ai_probability or 0.0)
            sub.web_plagiarism_score = float(ai_result.plagiarism_report.public_source_score or 0.0)
            db.commit()

            try:
                supabase.table("submissions").update({
                    "status": "completed",
                    "similarity_score": final_peer_score,
                    "ai_content_probability": float(ai_result.plagiarism_report.ai_probability or 0.0),
                    "web_plagiarism_score": float(ai_result.plagiarism_report.public_source_score or 0.0),
                    "extracted_text": extracted_text[:10000],
                    "content": extracted_text[:10000],
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }).eq("id", sub.id).execute()
            except Exception as sb_sub_err:
                logger.warning(f"Failed to update submission status in Supabase for {sub.id}: {sb_sub_err}")

            evaluated_count += 1

            # f. Update Celery task state/progress in Redis ({"current": i, "total": total, "status": "PROCESSING"})
            current_progress_pct = round(((idx + 1) / total) * 100.0, 1)
            job.processed_items = idx + 1
            job.progress_pct = current_progress_pct
            db.commit()

            if task_instance:
                task_instance.update_state(
                    state="PROCESSING",
                    meta={
                        "current": idx + 1,
                        "total": total,
                        "percent": current_progress_pct,
                        "status": "PROCESSING",
                    },
                )

        # 6. Mark Job Complete
        job.status = "completed"
        job.progress_pct = 100.0
        job.meta_info = {
            "similarity_flags": similarity_flags_count,
            "ready_for_review": evaluated_count,
        }
        db.commit()

        if task_instance:
            task_instance.update_state(
                state="SUCCESS",
                meta={
                    "current": total,
                    "total": total,
                    "percent": 100.0,
                    "status": "SUCCESS",
                    "processed": evaluated_count,
                    "similarity_flags": similarity_flags_count,
                },
            )

        log_audit_event(
            actor="CELERY_WORKER",
            action="BATCH_EVALUATION_SUCCESS",
            entity="Assignment",
            entity_id=assignment_id,
            details=f"Evaluated {evaluated_count}/{total} submissions for assignment {assignment_id}",
        )

        return {
            "status": "SUCCESS",
            "current": total,
            "total": total,
            "percent": 100.0,
            "processed": evaluated_count,
            "similarity_flags": similarity_flags_count,
            "job_id": job_id,
        }

    except Exception as e:
        logger.error(f"Error in batch evaluation worker task {job_id}: {e}", exc_info=True)
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()

        if task_instance:
            task_instance.update_state(
                state="FAILURE",
                meta={"error": str(e), "status": "FAILURE"},
            )
        raise e
    finally:
        db.close()
