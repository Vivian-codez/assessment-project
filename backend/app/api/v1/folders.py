"""Multi-tenant Assignment Folders & Evaluation API Router.

Provides user-scoped folder management, submission intake, monthly quota tracking,
and async Gemini evaluation pipeline endpoints with strict tenant isolation.
"""

import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.logging import logger
from app.models.user import User
from app.models.assignment_folder import (
    AssignmentFolder,
    Submission,
    EvaluationResult,
    MonthlyUsage,
)
from app.api.v1.auth import get_current_user
from app.api.v1.deps import get_user_scoped_folder
from app.services.quota_service import (
    check_and_increment_monthly_quota,
    get_or_create_monthly_usage,
    record_token_usage,
    DEFAULT_MONTHLY_QUOTA,
)
from app.services.tenant_gemini_service import tenant_gemini_evaluator
from app.schemas.tenant_evaluation import (
    AssignmentFolderCreate,
    AssignmentFolderUpdate,
    AssignmentFolderResponse,
    FolderSubmissionCreate,
    FolderSubmissionResponse,
    EvaluationResultResponse,
    MonthlyUsageResponse,
    EvaluateFolderResponse,
)

router = APIRouter(prefix="/folders", tags=["Tenant Folders & Evaluation"])


# ------------------------------------------------------------------------------
# Background Evaluation Worker
# ------------------------------------------------------------------------------
async def process_folder_evaluations(
    folder_id: str,
    user_id: str,
    rubric_text: str,
    submission_ids: List[str],
):
    """Background async worker grading submissions and persisting results to PostgreSQL."""
    db = SessionLocal()
    total_tokens = 0
    try:
        logger.info(f"[BG-EVAL-START] Starting evaluation for folder {folder_id} ({len(submission_ids)} submissions)")
        for sub_id in submission_ids:
            sub = db.query(Submission).filter(Submission.id == sub_id).first()
            if not sub:
                continue

            try:
                # Execute async evaluation via Gemini (isolated per submission)
                result, tokens = await tenant_gemini_evaluator.evaluate_submission(
                    rubric_text=rubric_text,
                    extracted_text=sub.extracted_text or sub.content or "",
                    student_identifier=sub.student_identifier,
                )
                total_tokens += tokens

                # Upsert EvaluationResult record
                eval_record = db.query(EvaluationResult).filter(EvaluationResult.submission_id == sub.id).first()
                if not eval_record:
                    eval_record = EvaluationResult(
                        id=str(uuid.uuid4()),
                        submission_id=sub.id,
                        score=result.score,
                        feedback_json={
                            "feedback": result.feedback,
                            "criteria_breakdown": result.criteria_breakdown,
                            "improvement_areas": result.improvement_areas,
                        },
                        evaluated_at=datetime.now(timezone.utc),
                    )
                    db.add(eval_record)
                else:
                    eval_record.score = result.score
                    eval_record.feedback_json = {
                        "feedback": result.feedback,
                        "criteria_breakdown": result.criteria_breakdown,
                        "improvement_areas": result.improvement_areas,
                    }
                    eval_record.evaluated_at = datetime.now(timezone.utc)

                sub.evaluation_status = "completed"
                db.commit()

            except Exception as item_err:
                logger.error(f"[BG-EVAL-ITEM-ERR] Failed evaluating submission {sub_id}: {item_err}")
                sub.evaluation_status = "deferred"
                db.commit()

        # Mark parent folder completed
        folder = db.query(AssignmentFolder).filter(AssignmentFolder.id == folder_id).first()
        if folder:
            folder.status = "completed"
            db.commit()

        # Update accumulated token count
        if total_tokens > 0:
            record_token_usage(db, user_id=user_id, token_count=total_tokens)

        logger.info(f"[BG-EVAL-FINISH] Completed batch for folder {folder_id}; consumed {total_tokens} tokens")

    except Exception as batch_err:
        logger.exception(f"[BG-EVAL-BATCH-ERR] Unhandled error in background folder evaluation: {batch_err}")
    finally:
        db.close()


# ------------------------------------------------------------------------------
# Assignment Folder CRUD Endpoints (Strict Tenant Isolation)
# ------------------------------------------------------------------------------
@router.post("", response_model=AssignmentFolderResponse, status_code=status.HTTP_201_CREATED)
def create_folder(
    payload: AssignmentFolderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Creates a new assignment folder scoped strictly to the authenticated tenant user."""
    try:
        folder = AssignmentFolder(
            id=str(uuid.uuid4()),
            user_id=str(current_user.id),
            title=payload.title.strip(),
            rubric_text=payload.rubric_text.strip(),
            status="pending",
        )
        db.add(folder)
        db.commit()
        db.refresh(folder)
        logger.info(f"[FOLDER-CREATED] Folder {folder.id} created by user {current_user.id}")
        return AssignmentFolderResponse(
            id=str(folder.id),
            user_id=str(folder.user_id),
            title=folder.title,
            rubric_text=folder.rubric_text,
            status=folder.status,
            created_at=folder.created_at,
            submission_count=0,
            submissions=[],
        )
    except Exception as exc:
        logger.exception(f"[FOLDER-CREATE-ERR] Failed creating assignment folder: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating assignment folder.",
        )


@router.get("", response_model=List[AssignmentFolderResponse])
def list_folders(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists all assignment folders belonging to current_user (strict tenant isolation)."""
    try:
        folders = (
            db.query(AssignmentFolder)
            .filter(AssignmentFolder.user_id == str(current_user.id))
            .order_by(AssignmentFolder.created_at.desc())
            .all()
        )
        results = []
        for f in folders:
            sub_count = db.query(Submission).filter(Submission.folder_id == f.id).count()
            results.append(
                AssignmentFolderResponse(
                    id=str(f.id),
                    user_id=str(f.user_id),
                    title=f.title,
                    rubric_text=f.rubric_text,
                    status=f.status,
                    created_at=f.created_at,
                    submission_count=sub_count,
                    submissions=[],
                )
            )
        return results
    except Exception as exc:
        logger.exception(f"[FOLDER-LIST-ERR] Error retrieving folders: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching assignment folders.",
        )


@router.get("/{folder_id}", response_model=AssignmentFolderResponse)
def get_folder_details(
    folder: AssignmentFolder = Depends(get_user_scoped_folder),
    db: Session = Depends(get_db),
):
    """Retrieves an assignment folder with its submissions, enforcing tenant scope."""
    try:
        submissions = (
            db.query(Submission)
            .filter(Submission.folder_id == folder.id)
            .order_by(Submission.created_at.asc())
            .all()
        )
        sub_responses = []
        for s in submissions:
            eval_res = None
            if s.evaluation_result:
                eval_res = EvaluationResultResponse(
                    id=str(s.evaluation_result.id),
                    submission_id=str(s.evaluation_result.submission_id),
                    score=s.evaluation_result.score,
                    feedback_json=s.evaluation_result.feedback_json or {},
                    evaluated_at=s.evaluation_result.evaluated_at,
                )
            sub_responses.append(
                FolderSubmissionResponse(
                    id=str(s.id),
                    folder_id=str(s.folder_id),
                    student_identifier=s.student_identifier,
                    file_path=s.file_path,
                    extracted_text=s.extracted_text,
                    evaluation_status=s.evaluation_status or "unprocessed",
                    created_at=s.created_at,
                    evaluation=eval_res,
                )
            )

        return AssignmentFolderResponse(
            id=str(folder.id),
            user_id=str(folder.user_id),
            title=folder.title,
            rubric_text=folder.rubric_text,
            status=folder.status,
            created_at=folder.created_at,
            submission_count=len(sub_responses),
            submissions=sub_responses,
        )
    except Exception as exc:
        logger.exception(f"[FOLDER-DETAIL-ERR] Error fetching folder details: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching folder details.",
        )


@router.delete("/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_folder(
    folder: AssignmentFolder = Depends(get_user_scoped_folder),
    db: Session = Depends(get_db),
):
    """Deletes an assignment folder and cascades deletion to linked submissions."""
    try:
        db.delete(folder)
        db.commit()
        logger.info(f"[FOLDER-DELETED] Folder {folder.id} deleted successfully.")
    except Exception as exc:
        logger.exception(f"[FOLDER-DEL-ERR] Error deleting folder {folder.id}: {exc}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error deleting assignment folder.",
        )


# ------------------------------------------------------------------------------
# Submission Intake Endpoints
# ------------------------------------------------------------------------------
@router.post("/{folder_id}/submissions", response_model=FolderSubmissionResponse, status_code=status.HTTP_201_CREATED)
def add_submission_to_folder(
    payload: FolderSubmissionCreate,
    folder: AssignmentFolder = Depends(get_user_scoped_folder),
    db: Session = Depends(get_db),
):
    """Adds a student submission document to an assignment folder."""
    try:
        sub = Submission(
            id=str(uuid.uuid4()),
            folder_id=str(folder.id),
            student_identifier=payload.student_identifier.strip(),
            extracted_text=payload.extracted_text,
            file_path=payload.file_path,
            evaluation_status="unprocessed",
        )
        db.add(sub)
        db.commit()
        db.refresh(sub)
        logger.info(f"[SUBMISSION-ADDED] Added submission {sub.id} (student={sub.student_identifier}) to folder {folder.id}")

        return FolderSubmissionResponse(
            id=str(sub.id),
            folder_id=str(sub.folder_id),
            student_identifier=sub.student_identifier,
            file_path=sub.file_path,
            extracted_text=sub.extracted_text,
            evaluation_status=sub.evaluation_status,
            created_at=sub.created_at,
            evaluation=None,
        )
    except Exception as exc:
        logger.exception(f"[SUBMISSION-ADD-ERR] Failed adding submission: {exc}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error creating student submission.",
        )


# ------------------------------------------------------------------------------
# Core Evaluation Endpoint with Graceful Quota Handling
# ------------------------------------------------------------------------------
@router.post("/{folder_id}/evaluate", response_model=EvaluateFolderResponse, status_code=status.HTTP_200_OK)
async def evaluate_folder(
    folder_id: str,
    background_tasks: BackgroundTasks,
    sync: bool = Query(False, description="Whether to execute evaluation synchronously before replying (useful for testing)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Triggers multi-tenant AI assignment evaluation for all unprocessed submissions in a folder.

    Validates:
    1. Folder ownership and tenant isolation.
    2. Monthly usage and quota limits.
       - If quota is exhausted: marks submissions 'quota_deferred' and returns a structured 200 response.
       - If quota is available: atomically decrements quota and enqueues evaluation.
    """
    try:
        # Step 1: Validate tenant isolation (folder must belong to current_user)
        folder = (
            db.query(AssignmentFolder)
            .filter(
                AssignmentFolder.id == str(folder_id),
                AssignmentFolder.user_id == str(current_user.id),
            )
            .first()
        )
        if not folder:
            logger.warning(f"[EVAL-DENIED] User {current_user.id} requested unauthorized folder {folder_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Assignment folder not found or access denied.",
            )

        # Step 2: Query all unprocessed submissions in this folder
        unprocessed_submissions = (
            db.query(Submission)
            .filter(
                Submission.folder_id == folder.id,
                Submission.evaluation_status.in_(["unprocessed", "pending", "quota_deferred", None]),
            )
            .all()
        )

        unprocessed_count = len(unprocessed_submissions)
        if unprocessed_count == 0:
            return EvaluateFolderResponse(
                status="completed",
                folder_id=str(folder.id),
                queued_submissions=0,
                deferred_submissions=0,
                message="No unprocessed submissions found in this folder.",
            )

        # Step 3: Check monthly quota gracefully
        allowed, usage, remaining = check_and_increment_monthly_quota(
            db=db,
            user_id=str(current_user.id),
            count=unprocessed_count,
            max_quota=DEFAULT_MONTHLY_QUOTA,
        )

        # Step 4: Handle Quota Exhaustion Gracefully (Return 200 with quota_deferred, NO 500 error)
        if not allowed:
            logger.info(f"[EVAL-QUOTA-DEFERRED] Marking {unprocessed_count} submissions as quota_deferred for user={current_user.id}")
            for sub in unprocessed_submissions:
                sub.evaluation_status = "quota_deferred"
            db.commit()

            return EvaluateFolderResponse(
                status="quota_deferred",
                folder_id=str(folder.id),
                queued_submissions=0,
                deferred_submissions=unprocessed_count,
                message=(
                    f"Monthly evaluation quota exhausted ({usage.submissions_evaluated}/{DEFAULT_MONTHLY_QUOTA}). "
                    f"{unprocessed_count} submission(s) have been queued and marked as quota_deferred."
                ),
            )

        # Step 5: Quota available -> transition submissions to 'processing' and folder to 'processing'
        for sub in unprocessed_submissions:
            sub.evaluation_status = "processing"
        folder.status = "processing"
        db.commit()

        submission_ids = [str(s.id) for s in unprocessed_submissions]

        # Step 6: Dispatch async evaluation
        if sync:
            # Synchronous execution (useful for instant verification in integration tests)
            await process_folder_evaluations(
                folder_id=str(folder.id),
                user_id=str(current_user.id),
                rubric_text=folder.rubric_text,
                submission_ids=submission_ids,
            )
            return EvaluateFolderResponse(
                status="completed",
                folder_id=str(folder.id),
                queued_submissions=unprocessed_count,
                deferred_submissions=0,
                message=f"Successfully evaluated {unprocessed_count} submission(s).",
            )
        else:
            # Asynchronous background tasks execution
            background_tasks.add_task(
                process_folder_evaluations,
                folder_id=str(folder.id),
                user_id=str(current_user.id),
                rubric_text=folder.rubric_text,
                submission_ids=submission_ids,
            )
            return EvaluateFolderResponse(
                status="processing",
                folder_id=str(folder.id),
                queued_submissions=unprocessed_count,
                deferred_submissions=0,
                message=f"Enqueued {unprocessed_count} submission(s) for AI evaluation.",
            )

    except HTTPException:
        # Re-raise standard HTTP exceptions
        raise
    except Exception as exc:
        # Step 7: Error Sanitization (Log internally; never leak stack traces)
        logger.exception(f"[EVAL-ENDPOINT-ERR] Uncaught exception evaluating folder {folder_id}: {exc}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error processing assignment evaluation.",
        )


# ------------------------------------------------------------------------------
# Monthly Usage Endpoint
# ------------------------------------------------------------------------------
@router.get("/usage/monthly", response_model=MonthlyUsageResponse)
def get_monthly_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Returns the authenticated tenant user's monthly evaluation quota and consumption metrics."""
    try:
        usage = get_or_create_monthly_usage(db=db, user_id=str(current_user.id))
        remaining = max(0, DEFAULT_MONTHLY_QUOTA - usage.submissions_evaluated)
        return MonthlyUsageResponse(
            user_id=str(usage.user_id),
            billing_month=usage.billing_month,
            submissions_evaluated=usage.submissions_evaluated,
            token_count=usage.token_count,
            quota_limit=DEFAULT_MONTHLY_QUOTA,
            remaining_quota=remaining,
        )
    except Exception as exc:
        logger.exception(f"[USAGE-ENDPOINT-ERR] Error fetching monthly usage: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error fetching monthly usage metrics.",
        )
