# Module docstring explaining comprehensive initial Alembic migration
"""Comprehensive initial PostgreSQL database schema for Verism AI SaaS.

Revision ID: 0001_initial_schema
Revises: None
Create Date: 2026-11-21 00:00:00.000000

Creates foundational tables with UUID primary keys, timezone-aware UTC timestamps,
explicit foreign key cascades, and performance indexes:
- organizations, users, user_sessions, refresh_tokens, instructors
- classrooms, courses, sections, students, enrollments
- rubrics, rubric_criteria, rubric_tiers
- assignments, reference_files, assignment_folders
- submissions, folder_submissions, submission_files
- batch_jobs, grading_runs, draft_grades, criterion_scores, evaluation_results, monthly_usages
- similarity_matches, integrity_flags, exports, audit_logs, deletion_requests
"""

# Import typing Sequence and Union for Alembic typing compliance
from typing import Sequence, Union
# Import Alembic operations module
from alembic import op
# Import SQLAlchemy primitives
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Apply initial schema migration creating all foundational tables and indexes."""

    # 1. Organizations table
    op.create_table(
        "organizations",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("slug", sa.String(length=128), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_organizations_domain", "organizations", ["domain"])
    op.create_index("idx_organizations_slug", "organizations", ["slug"])

    # 2. Users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("full_name", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("email", sa.String(length=255), unique=True, nullable=False),
        sa.Column("role", sa.String(length=128), server_default="Instructor · Computer Science", nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("email_verified", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("verification_token", sa.String(length=255), nullable=True),
        sa.Column("password_reset_token", sa.String(length=255), nullable=True),
        sa.Column("password_reset_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_users_email", "users", ["email"])
    op.create_index("idx_users_organization_id", "users", ["organization_id"])

    # 3. Refresh Tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=255), unique=True, nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("idx_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"])

    # 4. User Sessions table
    op.create_table(
        "user_sessions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token", sa.String(length=512), nullable=False),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_user_sessions_user_id", "user_sessions", ["user_id"])
    op.create_index("idx_user_sessions_token", "user_sessions", ["token"])

    # 5. Instructors table (backward-compatible mirror)
    op.create_table(
        "instructors",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), unique=True, nullable=False),
        sa.Column("role", sa.String(length=128), server_default="Instructor · Computer Science", nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_instructors_email", "instructors", ["email"])

    # 6. Classrooms table
    op.create_table(
        "classrooms",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("instructor_id", sa.String(length=64), sa.ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_classrooms_instructor_id", "classrooms", ["instructor_id"])
    op.create_index("idx_classrooms_code", "classrooms", ["code"])

    # 7. Courses table
    op.create_table(
        "courses",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("organization_id", sa.String(length=36), sa.ForeignKey("organizations.id", ondelete="SET NULL"), nullable=True),
        sa.Column("instructor_id", sa.String(length=64), sa.ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("section", sa.String(length=32), server_default="A", nullable=False),
        sa.Column("tone", sa.String(length=32), server_default="lav", nullable=False),
        sa.Column("students_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_courses_user_id", "courses", ["user_id"])
    op.create_index("idx_courses_organization_id", "courses", ["organization_id"])
    op.create_index("idx_courses_code", "courses", ["code"])

    # 8. Sections table
    op.create_table(
        "sections",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("course_id", sa.String(length=64), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_sections_course_id", "sections", ["course_id"])

    # 9. Students table
    op.create_table(
        "students",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("classroom_id", sa.String(length=64), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=False),
        sa.Column("roll_number", sa.String(length=64), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("classroom_id", "roll_number", name="uq_students_classroom_roll"),
    )
    op.create_index("idx_students_classroom_id", "students", ["classroom_id"])
    op.create_index("idx_students_roll_number", "students", ["roll_number"])

    # 10. Enrollments table
    op.create_table(
        "enrollments",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("student_id", sa.String(length=64), sa.ForeignKey("students.id", ondelete="CASCADE"), nullable=False),
        sa.Column("course_id", sa.String(length=64), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("section_id", sa.String(length=36), sa.ForeignKey("sections.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="active", nullable=False),
        sa.Column("enrolled_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("student_id", "course_id", name="uq_enrollment_student_course"),
    )
    op.create_index("idx_enrollments_student_id", "enrollments", ["student_id"])
    op.create_index("idx_enrollments_course_id", "enrollments", ["course_id"])

    # 11. Rubrics table
    op.create_table(
        "rubrics",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("classroom_id", sa.String(length=64), sa.ForeignKey("classrooms.id", ondelete="CASCADE"), nullable=True),
        sa.Column("course_id", sa.String(length=64), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("total_marks", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("total_max_score", sa.Float(), server_default="100.0", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_rubrics_course_id", "rubrics", ["course_id"])
    op.create_index("idx_rubrics_classroom_id", "rubrics", ["classroom_id"])

    # 12. Rubric Criteria table
    op.create_table(
        "rubric_criteria",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("rubric_id", sa.String(length=64), sa.ForeignKey("rubrics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_name", sa.String(length=255), nullable=True),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("weight", sa.Float(), server_default="25.0", nullable=False),
        sa.Column("max_points", sa.Float(), server_default="4.0", nullable=False),
        sa.Column("max_score", sa.Float(), server_default="4.0", nullable=False),
        sa.Column("order_index", sa.Integer(), server_default="0", nullable=False),
        sa.Column("levels", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_rubric_criteria_rubric_id", "rubric_criteria", ["rubric_id"])

    # 13. Rubric Tiers table
    op.create_table(
        "rubric_tiers",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("criterion_id", sa.String(length=64), sa.ForeignKey("rubric_criteria.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("points", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_rubric_tiers_criterion_id", "rubric_tiers", ["criterion_id"])

    # 14. Assignments table
    op.create_table(
        "assignments",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("course_id", sa.String(length=64), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.Column("max_score", sa.Float(), server_default="100.0", nullable=False),
        sa.Column("rubric_id", sa.String(length=64), sa.ForeignKey("rubrics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reference_assignment_text", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="Draft", nullable=False),
        sa.Column("assignment_type", sa.String(length=64), server_default="homework", nullable=False),
        sa.Column("similarity_threshold", sa.Float(), server_default="70.0", nullable=False),
        sa.Column("starter_code", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_assignments_course_id", "assignments", ["course_id"])
    op.create_index("idx_assignments_rubric_id", "assignments", ["rubric_id"])
    op.create_index("idx_assignments_status", "assignments", ["status"])

    # 15. Reference Files table
    op.create_table(
        "reference_files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_reference_files_assignment_id", "reference_files", ["assignment_id"])

    # 16. Assignment Folders table
    op.create_table(
        "assignment_folders",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("rubric_text", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_assignment_folders_user_id", "assignment_folders", ["user_id"])
    op.create_index("idx_assignment_folders_status", "assignment_folders", ["status"])

    # 17. Submissions table
    op.create_table(
        "submissions",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True),
        sa.Column("folder_id", sa.String(length=64), sa.ForeignKey("assignment_folders.id", ondelete="CASCADE"), nullable=True),
        sa.Column("classroom_id", sa.String(length=64), sa.ForeignKey("classrooms.id", ondelete="SET NULL"), nullable=True),
        sa.Column("student_id", sa.String(length=64), sa.ForeignKey("students.id", ondelete="SET NULL"), nullable=True),
        sa.Column("student_identifier", sa.String(length=255), nullable=True),
        sa.Column("student_name_encrypted", sa.Text(), nullable=True),
        sa.Column("student_roll_encrypted", sa.Text(), nullable=True),
        sa.Column("student_email_encrypted", sa.Text(), nullable=True),
        sa.Column("file_name", sa.String(length=255), server_default="submission.txt", nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("file_type", sa.String(length=64), server_default="pdf", nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("content", sa.Text(), nullable=True),
        sa.Column("file_content", sa.Text(), nullable=True),
        sa.Column("evaluation_status", sa.String(length=32), server_default="unprocessed", nullable=False),
        sa.Column("similarity_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("ai_content_probability", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("web_plagiarism_score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("web_sources", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_submissions_assignment_id", "submissions", ["assignment_id"])
    op.create_index("idx_submissions_folder_id", "submissions", ["folder_id"])
    op.create_index("idx_submissions_student_id", "submissions", ["student_id"])
    op.create_index("idx_submissions_status", "submissions", ["status"])
    op.create_index("idx_submissions_evaluation_status", "submissions", ["evaluation_status"])

    # 18. Folder Submissions table
    op.create_table(
        "folder_submissions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("folder_id", sa.String(length=36), sa.ForeignKey("assignment_folders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("student_identifier", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("evaluation_status", sa.String(length=32), server_default="unprocessed", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_folder_submissions_folder_id", "folder_submissions", ["folder_id"])
    op.create_index("idx_folder_submissions_student_identifier", "folder_submissions", ["student_identifier"])

    # 19. Submission Files table
    op.create_table(
        "submission_files",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("submission_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("file_type", sa.String(length=64), server_default="pdf", nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_submission_files_submission_id", "submission_files", ["submission_id"])

    # 20. Batch Jobs table
    op.create_table(
        "batch_jobs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assignment_id", sa.String(length=64), nullable=True),
        sa.Column("job_type", sa.String(length=64), server_default="batch_evaluation", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("progress_pct", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("total_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("processed_items", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("meta_info", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_batch_jobs_assignment_id", "batch_jobs", ["assignment_id"])
    op.create_index("idx_batch_jobs_status", "batch_jobs", ["status"])

    # 21. Grading Runs table
    op.create_table(
        "grading_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("triggered_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="queued", nullable=False),
        sa.Column("total_submissions", sa.Integer(), server_default="0", nullable=False),
        sa.Column("completed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_grading_runs_assignment_id", "grading_runs", ["assignment_id"])
    op.create_index("idx_grading_runs_status", "grading_runs", ["status"])

    # 22. Draft Grades table
    op.create_table(
        "draft_grades",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("submission_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("suggested_score", sa.Float(), server_default="0.0", nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("max_score", sa.Float(), server_default="100.0", nullable=True),
        sa.Column("final_score", sa.Float(), nullable=True),
        sa.Column("criteria_scores", sa.JSON(), nullable=False),
        sa.Column("criteria_breakdown", sa.JSON(), nullable=True),
        sa.Column("plagiarism_report", sa.JSON(), nullable=True),
        sa.Column("ai_feedback", sa.Text(), nullable=True),
        sa.Column("teacher_feedback", sa.Text(), nullable=True),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_draft_grades_submission_id", "draft_grades", ["submission_id"])
    op.create_index("idx_draft_grades_status", "draft_grades", ["status"])

    # 23. Criterion Scores table
    op.create_table(
        "criterion_scores",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("grade_id", sa.String(length=64), sa.ForeignKey("draft_grades.id", ondelete="CASCADE"), nullable=False),
        sa.Column("criterion_id", sa.String(length=64), sa.ForeignKey("rubric_criteria.id", ondelete="SET NULL"), nullable=True),
        sa.Column("criterion_name", sa.String(length=255), nullable=False),
        sa.Column("score", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("max_score", sa.Float(), server_default="100.0", nullable=False),
        sa.Column("feedback", sa.Text(), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_criterion_scores_grade_id", "criterion_scores", ["grade_id"])

    # 24. Evaluation Results table
    op.create_table(
        "evaluation_results",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("submission_id", sa.String(length=36), sa.ForeignKey("folder_submissions.id", ondelete="CASCADE"), unique=True, nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("feedback_json", sa.JSON(), nullable=False),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_evaluation_results_submission_id", "evaluation_results", ["submission_id"])

    # 25. Monthly Usages table
    op.create_table(
        "monthly_usages",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("billing_month", sa.String(length=7), nullable=False),
        sa.Column("submissions_evaluated", sa.Integer(), server_default="0", nullable=False),
        sa.Column("token_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("user_id", "billing_month", name="uq_user_billing_month"),
    )
    op.create_index("idx_monthly_usages_user_month", "monthly_usages", ["user_id", "billing_month"])

    # 26. Similarity Matches table
    op.create_table(
        "similarity_matches",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submission_a_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("submission_b_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("similarity_score", sa.Float(), nullable=False),
        sa.Column("matching_phrases", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=64), server_default="High similarity", nullable=False),
        sa.Column("teacher_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_similarity_matches_assignment_id", "similarity_matches", ["assignment_id"])
    op.create_index("idx_similarity_matches_sub_a", "similarity_matches", ["submission_a_id"])
    op.create_index("idx_similarity_matches_sub_b", "similarity_matches", ["submission_b_id"])

    # 27. Integrity Flags table
    op.create_table(
        "integrity_flags",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("submission_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("flag_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), server_default="medium", nullable=False),
        sa.Column("status", sa.String(length=32), server_default="new", nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("details", sa.JSON(), nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        sa.Column("resolved_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_integrity_flags_submission_id", "integrity_flags", ["submission_id"])
    op.create_index("idx_integrity_flags_resolved", "integrity_flags", ["resolved"])
    op.create_index("idx_integrity_flags_status", "integrity_flags", ["status"])

    # 28. Exports table
    op.create_table(
        "exports",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("course_id", sa.String(length=64), sa.ForeignKey("courses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("requested_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("export_type", sa.String(length=64), nullable=False),
        sa.Column("file_path", sa.String(length=512), nullable=True),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_exports_course_id", "exports", ["course_id"])

    # 29. Audit Logs table
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("actor_id", sa.String(length=64), sa.ForeignKey("instructors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("actor_name", sa.String(length=255), server_default="System", nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_audit_logs_action", "audit_logs", ["action"])
    op.create_index("idx_audit_logs_created_at", "audit_logs", ["created_at"])

    # 30. Deletion Requests table
    op.create_table(
        "deletion_requests",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.String(length=64), nullable=False),
        sa.Column("entity_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), server_default="completed", nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("idx_deletion_requests_user_id", "deletion_requests", ["user_id"])


def downgrade() -> None:
    """Drop all tables in reverse dependency order."""
    op.drop_table("deletion_requests")
    op.drop_table("audit_logs")
    op.drop_table("exports")
    op.drop_table("integrity_flags")
    op.drop_table("similarity_matches")
    op.drop_table("monthly_usages")
    op.drop_table("evaluation_results")
    op.drop_table("criterion_scores")
    op.drop_table("draft_grades")
    op.drop_table("grading_runs")
    op.drop_table("batch_jobs")
    op.drop_table("submission_files")
    op.drop_table("folder_submissions")
    op.drop_table("submissions")
    op.drop_table("assignment_folders")
    op.drop_table("reference_files")
    op.drop_table("assignments")
    op.drop_table("rubric_tiers")
    op.drop_table("rubric_criteria")
    op.drop_table("rubrics")
    op.drop_table("enrollments")
    op.drop_table("students")
    op.drop_table("sections")
    op.drop_table("courses")
    op.drop_table("classrooms")
    op.drop_table("instructors")
    op.drop_table("user_sessions")
    op.drop_table("refresh_tokens")
    op.drop_table("users")
    op.drop_table("organizations")

