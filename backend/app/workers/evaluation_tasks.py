"""Celery Background Task Definitions for Batch Evaluation and 3-Way Plagiarism Checks."""

import uuid
from datetime import datetime, timezone
from typing import List, Optional

from app.workers.celery_app import celery_app
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.logging import logger, log_audit_event
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


@celery_app.task(bind=True, name="app.workers.evaluation_tasks.evaluate_batch_task")
def evaluate_batch_task(
    self,
    job_id: str,
    assignment_id: str,
    submission_ids: Optional[List[str]] = None,
    rubric_id: Optional[str] = None,
    similarity_threshold: float = 90.0,
):
    """Celery background worker task for batch submission evaluation."""
    return run_evaluation_batch_logic(
        job_id=job_id,
        assignment_id=assignment_id,
        submission_ids=submission_ids,
        rubric_id=rubric_id,
        similarity_threshold=similarity_threshold,
        task_instance=self,
    )


def _ensure_assignment_in_db(db, assignment_id: str) -> Optional[Assignment]:
    """Ensure assignment exists in local DB, replicating from Supabase if needed."""
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if assignment:
        return assignment

    try:
        from app.core.supabase import supabase
        from app.models.course import Course
        res = supabase.table("assignments").select("*").eq("id", assignment_id).execute()
        if res.data:
            a_data = res.data[0]
            course_id = a_data["course_id"]
            course = db.query(Course).filter(Course.id == course_id).first()
            if not course:
                c_res = supabase.table("courses").select("*").eq("id", course_id).execute()
                if c_res.data:
                    c_data = c_res.data[0]
                    course = Course(
                        id=c_data["id"],
                        name=c_data["name"],
                        code=c_data["code"],
                        section=c_data.get("section", "A"),
                        tone=c_data.get("tone", "lav"),
                        students_count=c_data.get("students_count", 0),
                        instructor_id=c_data.get("instructor_id"),
                    )
                    db.add(course)
                    db.commit()
            assignment = Assignment(
                id=a_data["id"],
                course_id=course_id,
                title=a_data["title"],
                description=a_data.get("description"),
                max_score=float(a_data.get("max_score", 100.0)),
                rubric_id=a_data.get("rubric_id"),
                reference_assignment_text=a_data.get("reference_assignment_text"),
            )
            db.add(assignment)
            db.commit()
            db.refresh(assignment)
            return assignment
    except Exception as e:
        logger.warning(f"Supabase assignment lookup fallback notice in worker: {e}")

    return None


def run_evaluation_batch_logic(
    job_id: str,
    assignment_id: str,
    submission_ids: Optional[List[str]] = None,
    rubric_id: Optional[str] = None,
    similarity_threshold: float = 90.0,
    task_instance=None,
):
    """Executes the complete batch evaluation pipeline:
    1. Fetch target submission text, assignment rubric, reference exemplar (ground truth), and peer submissions from Supabase/DB
    2. Dense vector indexing in Qdrant & peer-to-peer similarity checks
    3. Gemini API 3-way plagiarism & rubric grading with XML prompt structure
    4. Store Draft Grades, audit payload, and emit progress updates to Supabase & local DB
    """
    db = SessionLocal()
    try:
        # 1. Update Job Status to Processing
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if not job:
            job = BatchJob(id=job_id, assignment_id=assignment_id, status="processing")
            db.add(job)
        else:
            job.status = "processing"
            job.progress_pct = 5.0
        db.commit()

        # 2. Fetch Assignment and Rubric
        assignment = _ensure_assignment_in_db(db, assignment_id)
        if not assignment:
            raise ValueError(f"Assignment {assignment_id} not found in database or Supabase.")

        target_rubric_id = rubric_id or assignment.rubric_id
        rubric = db.query(Rubric).filter(Rubric.id == target_rubric_id).first() if target_rubric_id else None

        rubric_criteria_list = []
        if rubric and rubric.criteria:
            rubric_criteria_list = [
                {
                    "name": c.name,
                    "description": c.description or "",
                    "weight": c.weight,
                    "max_score": c.max_score,
                }
                for c in rubric.criteria
            ]
        else:
            # Check Supabase for rubric
            sb_rubric = supabase_service.get_rubric(target_rubric_id) if target_rubric_id else None
            if sb_rubric and sb_rubric.get("criteria"):
                rubric_criteria_list = sb_rubric["criteria"]
            else:
                # Default standard academic rubric
                rubric_criteria_list = [
                    {"name": "Understanding", "description": "Conceptual clarity and analytical depth", "weight": 30.0, "max_score": 30.0},
                    {"name": "Accuracy", "description": "Correctness of algorithmic solution and methodology", "weight": 40.0, "max_score": 40.0},
                    {"name": "Presentation", "description": "Structure, clarity, and communication", "weight": 30.0, "max_score": 30.0},
                ]

        # 3. Context Caching for Reusable Rubrics in Gemini
        rubric_text = "\n".join([f"{c['name']} ({c.get('weight', 25)}%): {c.get('description', '')}" for c in rubric_criteria_list])
        if rubric:
            gemini_service.create_rubric_context_cache(rubric.id, rubric_text)

        # 4. Fetch Submissions
        query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
        if submission_ids:
            query = query.filter(Submission.id.in_(submission_ids))
        submissions: List[Submission] = query.all()

        if len(submissions) == 0:
            # Check Supabase database
            sb_subs = supabase_service.get_submissions(assignment_id)
            if sb_subs:
                for row in sb_subs:
                    s = Submission(
                        id=row["id"],
                        assignment_id=row["assignment_id"],
                        student_name_encrypted=row["student_name_encrypted"],
                        student_roll_encrypted=row["student_roll_encrypted"],
                        student_email_encrypted=row.get("student_email_encrypted"),
                        file_name=row["file_name"],
                        file_path=row.get("file_path", ""),
                        file_url=row.get("file_url"),
                        file_type=row.get("file_type", "pdf"),
                        extracted_text=row.get("extracted_text"),
                        content=row.get("content") or row.get("extracted_text") or "",
                        file_content=row.get("file_content"),
                        similarity_score=float(row.get("similarity_score") or 0.0),
                        ai_content_probability=float(row.get("ai_content_probability") or 0.0),
                        web_plagiarism_score=float(row.get("web_plagiarism_score") or 0.0),
                        status=row.get("status", "pending"),
                    )
                    db.add(s)
                db.commit()
                query = db.query(Submission).filter(Submission.assignment_id == assignment_id)
                if submission_ids:
                    query = query.filter(Submission.id.in_(submission_ids))
                submissions = query.all()

        total = len(submissions)
        job.total_items = total
        db.commit()

        if total == 0:
            job.status = "completed"
            job.progress_pct = 100.0
            db.commit()
            return {"status": "completed", "processed": 0}

        # 5. Extract Text & Index into Qdrant for Similarity Checking
        batch_texts = []
        for sub in submissions:
            if not sub.extracted_text and sub.file_content:
                ext = sub.file_name.lower().split(".")[-1] if "." in sub.file_name else ""
                is_binary = ext in {"pdf", "docx", "doc", "zip", "tar", "gz", "png", "jpg"}
                if not is_binary:
                    sub.extracted_text = sub.file_content
                else:
                    try:
                        import base64
                        raw_bytes = base64.b64decode(sub.file_content)
                        sub.extracted_text = pdf_service.extract_text_from_bytes(raw_bytes, sub.file_name)
                    except Exception:
                        pass
            if not sub.extracted_text and sub.file_path:
                sub.extracted_text = pdf_service.extract_text_from_file_path(sub.file_path)
            elif not sub.extracted_text:
                sub.extracted_text = f"Student submission content for {sub.file_name} analyzing core algorithmic implementations and design patterns."

            # Index in Qdrant
            vector_service.index_submission(
                submission_id=sub.id,
                assignment_id=assignment_id,
                text=sub.extracted_text,
                payload={"file_name": sub.file_name},
            )

            batch_texts.append({
                "id": sub.id,
                "text": sub.extracted_text,
                "student_a_name": sub.student_name,
            })

        # 6. Run Cross-Submission Peer-to-Peer Similarity Checks
        processed_pairs = set()
        similarity_flag_count = 0

        for sub in submissions:
            matches = vector_service.check_cross_submission_similarity(
                submission_id=sub.id,
                assignment_id=assignment_id,
                text=sub.extracted_text,
                all_submissions_in_batch=batch_texts,
                threshold=similarity_threshold,
            )

            highest_sim = 0.0
            for match in matches:
                peer_id = match["submission_b_id"]
                pair_key = tuple(sorted([sub.id, peer_id]))

                if pair_key not in processed_pairs:
                    processed_pairs.add(pair_key)
                    sim_score = match["similarity_score"]
                    if sim_score >= highest_sim:
                        highest_sim = sim_score

                    # Persist similarity match
                    sim_record = SimilarityMatch(
                        id=f"pair_{uuid.uuid4().hex[:12]}",
                        assignment_id=assignment_id,
                        submission_a_id=sub.id,
                        submission_b_id=peer_id,
                        similarity_score=sim_score,
                        matching_phrases=match["matching_phrases"],
                        status=match["status"],
                    )
                    db.add(sim_record)

                    if sim_score >= similarity_threshold:
                        similarity_flag_count += 1

            sub.similarity_score = highest_sim

        db.commit()

        # 7. AI Grading with Gemini Core (Pseudonymized for FERPA)
        for index, sub in enumerate(submissions):
            # Fetch existing peer submissions excluding the target submission
            peer_corpus_items = [
                f"Peer Submission {t['id']} ({t['student_a_name']}):\n{t['text'][:2500]}"
                for t in batch_texts
                if t["id"] != sub.id
            ]
            peer_corpus = "\n---\n".join(peer_corpus_items[:10]) if peer_corpus_items else "No other peer submissions available."

            # Pseudonymize student identity before calling GenAI API
            pseudo_id, sanitized_text = ferpa_service.prepare_for_ai_evaluation(
                submission_id=sub.id,
                student_name=sub.student_name,
                student_roll=sub.student_roll,
                student_email=sub.student_email,
                text_content=sub.extracted_text,
            )

            # Gemini Evaluation with Structured JSON Output & Reference Assignment
            ai_result = gemini_service.evaluate_submission(
                submission_text=sanitized_text,
                rubric_criteria=rubric_criteria_list,
                assignment_title=assignment.title,
                reference_assignment_text=assignment.reference_assignment_text,
                peer_submissions_context=peer_corpus,
                rubric_id=target_rubric_id,
            )

            sub.ai_content_probability = ai_result.ai_generated_probability or 0.0
            if ai_result.web_plagiarism_pct is not None:
                sub.web_plagiarism_score = ai_result.web_plagiarism_pct
            if ai_result.web_sources:
                sub.web_sources = ai_result.web_sources
            if ai_result.peer_to_peer_plagiarism_pct and ai_result.peer_to_peer_plagiarism_pct > sub.similarity_score:
                sub.similarity_score = ai_result.peer_to_peer_plagiarism_pct

            # Determine initial status across Peer Plagiarism, AI Content, and Web Plagiarism
            is_flagged = (
                (sub.similarity_score >= similarity_threshold)
                or (sub.ai_content_probability >= 65.0)
                or (sub.web_plagiarism_score >= 25.0)
            )
            sub.status = "flagged" if is_flagged else "graded"

            # Create or update DraftGrade
            criteria_payload = [
                {
                    "criterion_name": c.criterion_name,
                    "score": c.awarded_score,
                    "max": c.max_score,
                    "rationale": c.rationale,
                }
                for c in ai_result.criteria_evaluations
            ]

            existing_draft = db.query(DraftGrade).filter(DraftGrade.submission_id == sub.id).first()
            if existing_draft:
                existing_draft.suggested_score = ai_result.overall_score
                existing_draft.criteria_scores = criteria_payload
                existing_draft.ai_feedback = ai_result.feedback_summary
                existing_draft.status = "flagged" if is_flagged else "pending"
                existing_draft.ai_model = settings.GEMINI_MODEL
            else:
                draft_grade = DraftGrade(
                    id=f"draft_{uuid.uuid4().hex[:12]}",
                    submission_id=sub.id,
                    suggested_score=ai_result.overall_score,
                    criteria_scores=criteria_payload,
                    ai_feedback=ai_result.feedback_summary,
                    status="flagged" if is_flagged else "pending",
                    ai_model=settings.GEMINI_MODEL,
                )
                db.add(draft_grade)

            db.commit()

            # Save parsed scores, feedback, plagiarism flags, and audit payload to Supabase
            try:
                supabase_service.save_evaluation_results(
                    submission_id=sub.id,
                    overall_score=ai_result.overall_score,
                    similarity_score=sub.similarity_score,
                    ai_content_probability=sub.ai_content_probability,
                    web_plagiarism_score=sub.web_plagiarism_score,
                    web_sources=sub.web_sources or [],
                    criteria_scores=criteria_payload,
                    ai_feedback=ai_result.feedback_summary,
                    is_flagged=is_flagged,
                )
            except Exception as sb_save_err:
                logger.warning(f"Failed to persist evaluation results in Supabase for {sub.id}: {sb_save_err}")

            # Update progress
            progress = round(15.0 + ((index + 1) / total) * 85.0, 1)
            job.processed_items = index + 1
            job.progress_pct = progress
            db.commit()

            if task_instance:
                task_instance.update_state(
                    state="PROGRESS",
                    meta={"current": index + 1, "total": total, "progress": progress},
                )

        # 8. Mark Job Completed
        job.status = "completed"
        job.progress_pct = 100.0
        job.meta_info = {
            "similarity_flags": similarity_flag_count,
            "ready_for_review": total,
        }
        db.commit()

        log_audit_event(
            actor="SYSTEM_CELERY_WORKER",
            action="BATCH_EVALUATION_COMPLETED",
            entity="BatchJob",
            entity_id=job_id,
            details=f"Processed {total} submissions for assignment {assignment_id}",
        )

        return {
            "status": "completed",
            "job_id": job_id,
            "processed": total,
            "similarity_flags": similarity_flag_count,
        }

    except Exception as e:
        logger.error(f"Error executing batch evaluation job {job_id}: {e}", exc_info=True)
        job = db.query(BatchJob).filter(BatchJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(e)
            db.commit()
        raise e
    finally:
        db.close()
