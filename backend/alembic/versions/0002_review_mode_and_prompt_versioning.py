# Module docstring explaining migration for Review Mode, Prompt Versioning, and Grade History
"""Alembic migration adding Review Mode, Prompt Versioning, Dry Runs, and Grade History.

Revision ID: 0002_review_mode_and_prompt_versioning
Revises: 0001_initial_schema
Create Date: 2026-11-22 00:00:00.000000

Adds tables supporting teacher-driven grading and meta-prompting:
- prompt_versions: version-controlled prompt templates with locked base instructions
- prompt_feedback: teacher flags and corrections on specific criteria
- dry_runs: isolated evaluation testing on sample submissions without persisting to gradebook
- dry_run_results: criteria-level before/after diffs and regression flags
- grade_history: immutable audit trail of score changes, AI suggestions, and teacher overrides
- review_progress: per-teacher navigation and review queue persistence
"""

# Import typing Sequence and Union for Alembic typing compliance
from typing import Sequence, Union
# Import Alembic operations module
from alembic import op
# Import SQLAlchemy primitives
import sqlalchemy as sa

# Revision identifiers, used by Alembic.
revision: str = "0002_review_mode_and_prompt_versioning"
# Previous migration identifier
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
# Branch labels
branch_labels: Union[str, Sequence[str], None] = None
# Dependencies
depends_on: Union[str, Sequence[str], None] = None


# Migration upgrade procedure
def upgrade() -> None:
    """Apply migration creating prompt versioning, review mode, and grade audit tables."""

    # 1. Prompt Versions table
    op.create_table(
        # Table identifier
        "prompt_versions",
        # Primary key UUID column
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Assignment association foreign key (nullable for global default templates)
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=True),
        # Monotonically increasing version number for the target assignment
        sa.Column("version_number", sa.Integer(), nullable=False),
        # Prompt functional type (grading, plagiarism_explanation)
        sa.Column("prompt_type", sa.String(length=64), server_default="grading", nullable=False),
        # Immutable system prompt base instructions enforcing core grading rules
        sa.Column("locked_base_instructions", sa.Text(), nullable=False),
        # Editable guidelines customized by the teacher for this assignment
        sa.Column("extra_teacher_instructions", sa.Text(), nullable=True),
        # Calibrated few-shot grading examples serialized as JSON
        sa.Column("few_shot_examples", sa.JSON(), nullable=True),
        # Similarity and AI detection score thresholds
        sa.Column("thresholds", sa.JSON(), nullable=True),
        # Changelog or release notes for this prompt revision
        sa.Column("note", sa.String(length=255), nullable=True),
        # User identifier of the teacher who authored or approved this version
        sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        # Flag indicating whether this is the currently active version for auto-grading
        sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
        # Creation timestamp with UTC timezone
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Index on assignment_id for fast lookup of assignment-specific prompts
    op.create_index("idx_prompt_versions_assignment_id", "prompt_versions", ["assignment_id"])
    # Index on is_active to quickly find the active production prompt
    op.create_index("idx_prompt_versions_is_active", "prompt_versions", ["is_active"])

    # 2. Prompt Feedback table
    op.create_table(
        # Table identifier
        "prompt_feedback",
        # Primary key UUID column
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Prompt version evaluated when this feedback was generated
        sa.Column("prompt_version_id", sa.String(length=36), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        # Target submission identifier
        sa.Column("submission_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        # Target assignment identifier
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        # Target rubric criterion identifier
        sa.Column("criterion_id", sa.String(length=64), nullable=True),
        # AI-assigned rubric tier identifier
        sa.Column("ai_tier_id", sa.String(length=64), nullable=True),
        # Teacher-corrected rubric tier identifier
        sa.Column("teacher_tier_id", sa.String(length=64), nullable=True),
        # AI suggested criterion score
        sa.Column("ai_score", sa.Float(), nullable=True),
        # Teacher overridden criterion score
        sa.Column("teacher_score", sa.Float(), nullable=True),
        # Categorized reason code (e.g. too_harsh, too_lenient, missed_evidence)
        sa.Column("reason", sa.String(length=128), nullable=False),
        # Teacher qualitative notes and feedback
        sa.Column("teacher_notes", sa.Text(), nullable=True),
        # User identifier of the teacher who created the feedback
        sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        # Resolution flag
        sa.Column("resolved", sa.Boolean(), server_default="false", nullable=False),
        # Creation timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Index on prompt_version_id
    op.create_index("idx_prompt_feedback_prompt_version", "prompt_feedback", ["prompt_version_id"])
    # Index on submission_id
    op.create_index("idx_prompt_feedback_submission", "prompt_feedback", ["submission_id"])

    # 3. Dry Runs table
    op.create_table(
        # Table identifier
        "dry_runs",
        # Primary key UUID column
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Baseline prompt version being compared against
        sa.Column("prompt_version_id", sa.String(length=36), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        # Target assignment identifier
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        # Array of submission UUIDs selected as the test benchmark cohort
        sa.Column("sample_submission_ids", sa.JSON(), nullable=False),
        # Proposed candidate prompt instructions being tested
        sa.Column("draft_extra_instructions", sa.Text(), nullable=True),
        # Proposed candidate few-shot examples
        sa.Column("draft_few_shot_examples", sa.JSON(), nullable=True),
        # Execution status (pending, running, completed, failed)
        sa.Column("status", sa.String(length=32), server_default="pending", nullable=False),
        # Aggregate performance metrics (agreement_rate, score_delta, regressions)
        sa.Column("summary_metrics", sa.JSON(), nullable=True),
        # Teacher who launched the dry run
        sa.Column("created_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        # Creation timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Completion timestamp
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    # Index on assignment_id
    op.create_index("idx_dry_runs_assignment_id", "dry_runs", ["assignment_id"])

    # 4. Dry Run Results table
    op.create_table(
        # Table identifier
        "dry_run_results",
        # Primary key UUID column
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Parent dry run identifier
        sa.Column("dry_run_id", sa.String(length=36), sa.ForeignKey("dry_runs.id", ondelete="CASCADE"), nullable=False),
        # Submission evaluated
        sa.Column("submission_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        # Criterion evaluated
        sa.Column("criterion_id", sa.String(length=64), nullable=True),
        # Old tier identifier
        sa.Column("old_tier_id", sa.String(length=64), nullable=True),
        # New candidate tier identifier
        sa.Column("new_tier_id", sa.String(length=64), nullable=True),
        # Teacher ground-truth tier identifier
        sa.Column("teacher_corrected_tier_id", sa.String(length=64), nullable=True),
        # Old score points
        sa.Column("old_points", sa.Float(), nullable=True),
        # New score points
        sa.Column("new_points", sa.Float(), nullable=True),
        # Teacher ground truth points
        sa.Column("teacher_points", sa.Float(), nullable=True),
        # Regression flag indicating accuracy got worse
        sa.Column("is_regression", sa.Boolean(), server_default="false", nullable=False),
        # Old explanation text
        sa.Column("old_justification", sa.Text(), nullable=True),
        # New candidate explanation text
        sa.Column("new_justification", sa.Text(), nullable=True),
        # Old cited evidence quotes
        sa.Column("old_evidence", sa.JSON(), nullable=True),
        # New cited evidence quotes
        sa.Column("new_evidence", sa.JSON(), nullable=True),
        # Timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Index on dry_run_id
    op.create_index("idx_dry_run_results_dry_run_id", "dry_run_results", ["dry_run_id"])
    # Index on submission_id
    op.create_index("idx_dry_run_results_submission_id", "dry_run_results", ["submission_id"])

    # 5. Grade History table
    op.create_table(
        # Table identifier
        "grade_history",
        # Primary key UUID column
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Associated draft grade identifier
        sa.Column("draft_grade_id", sa.String(length=64), sa.ForeignKey("draft_grades.id", ondelete="SET NULL"), nullable=True),
        # Submission identifier
        sa.Column("submission_id", sa.String(length=64), sa.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False),
        # Assignment identifier
        sa.Column("assignment_id", sa.String(length=64), sa.ForeignKey("assignments.id", ondelete="CASCADE"), nullable=False),
        # Prompt version that produced this score
        sa.Column("prompt_version_id", sa.String(length=36), sa.ForeignKey("prompt_versions.id", ondelete="SET NULL"), nullable=True),
        # Total score awarded
        sa.Column("score", sa.Float(), nullable=True),
        # Maximum possible score
        sa.Column("max_score", sa.Float(), server_default="100.0", nullable=False),
        # Summary criteria scores dictionary
        sa.Column("criteria_scores", sa.JSON(), nullable=True),
        # Detailed criteria breakdown with evidence quotes
        sa.Column("criteria_breakdown", sa.JSON(), nullable=True),
        # Qualitative feedback text
        sa.Column("feedback", sa.Text(), nullable=True),
        # Status (graded, approved, overridden)
        sa.Column("status", sa.String(length=32), server_default="graded", nullable=False),
        # Type of change (initial_ai, regrade, manual_override, approved, rollback)
        sa.Column("change_type", sa.String(length=64), server_default="initial_ai", nullable=False),
        # User who performed the change (teacher UUID or system)
        sa.Column("changed_by", sa.String(length=64), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        # Rationale explanation for score adjustment
        sa.Column("change_reason", sa.Text(), nullable=True),
        # Timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    # Index on submission_id
    op.create_index("idx_grade_history_submission_id", "grade_history", ["submission_id"])
    # Index on assignment_id
    op.create_index("idx_grade_history_assignment_id", "grade_history", ["assignment_id"])
    # Index on change_type
    op.create_index("idx_grade_history_change_type", "grade_history", ["change_type"])

    # 6. Review Progress table
    op.create_table(
        # Table identifier
        "review_progress",
        # Primary key UUID column
        sa.Column("id", sa.String(length=36), primary_key=True),
        # Teacher user identifier
        sa.Column("user_id", sa.String(length=64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        # Context scope identifier ('all', course_id, or assignment_id)
        sa.Column("scope_key", sa.String(length=128), server_default="all", nullable=False),
        # Last reviewed submission identifier for state resumption
        sa.Column("last_viewed_submission_id", sa.String(length=64), nullable=True),
        # Active filter settings preserved across sessions
        sa.Column("last_filters", sa.JSON(), nullable=True),
        # Total count of approved/reviewed submissions
        sa.Column("reviewed_count", sa.Integer(), server_default="0", nullable=False),
        # Total submissions in current scope
        sa.Column("total_count", sa.Integer(), server_default="0", nullable=False),
        # Record creation timestamp
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        # Last updated timestamp
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        # Unique constraint per user and scope
        sa.UniqueConstraint("user_id", "scope_key", name="uq_review_progress_user_scope"),
    )
    # Index on user_id
    op.create_index("idx_review_progress_user_id", "review_progress", ["user_id"])


# Migration downgrade procedure
def downgrade() -> None:
    """Drop Review Mode and Prompt Versioning tables in reverse dependency order."""
    # Drop review_progress table
    op.drop_table("review_progress")
    # Drop grade_history table
    op.drop_table("grade_history")
    # Drop dry_run_results table
    op.drop_table("dry_run_results")
    # Drop dry_runs table
    op.drop_table("dry_runs")
    # Drop prompt_feedback table
    op.drop_table("prompt_feedback")
    # Drop prompt_versions table
    op.drop_table("prompt_versions")
