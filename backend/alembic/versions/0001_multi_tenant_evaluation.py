"""Multi-tenant user-scoped AI assignment evaluation pipeline.

Revision ID: 0001_multi_tenant_evaluation
Revises: 
Create Date: 2026-11-07 23:05:00.000000

Creates:
- assignment_folders table
- evaluation_results table
- monthly_usages table (with unique constraint on user_id, billing_month)
- folder_id, student_identifier, evaluation_status columns on submissions
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0001_multi_tenant_evaluation'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create assignment_folders table
    op.create_table(
        'assignment_folders',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('rubric_text', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_assignment_folders_user_id', 'assignment_folders', ['user_id'])
    op.create_index('idx_assignment_folders_status', 'assignment_folders', ['status'])

    # 2. Create folder_submissions table
    op.create_table(
        'folder_submissions',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('folder_id', sa.String(length=36), sa.ForeignKey('assignment_folders.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_identifier', sa.String(length=255), nullable=True),
        sa.Column('file_path', sa.String(length=512), nullable=True),
        sa.Column('extracted_text', sa.Text(), nullable=True),
        sa.Column('evaluation_status', sa.String(length=32), server_default='unprocessed', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_folder_submissions_folder_id', 'folder_submissions', ['folder_id'])
    op.create_index('idx_folder_submissions_student_identifier', 'folder_submissions', ['student_identifier'])
    op.create_index('idx_folder_submissions_evaluation_status', 'folder_submissions', ['evaluation_status'])

    # 3. Create evaluation_results table
    op.create_table(
        'evaluation_results',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('submission_id', sa.String(length=36), sa.ForeignKey('folder_submissions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('score', sa.Float(), nullable=False),
        sa.Column('feedback_json', sa.JSON(), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('idx_evaluation_results_submission_id', 'evaluation_results', ['submission_id'])

    # 4. Create monthly_usages table
    op.create_table(
        'monthly_usages',
        sa.Column('id', sa.String(length=36), primary_key=True),
        sa.Column('user_id', sa.String(length=64), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('billing_month', sa.String(length=7), nullable=False),
        sa.Column('submissions_evaluated', sa.Integer(), server_default='0', nullable=False),
        sa.Column('token_count', sa.BigInteger(), server_default='0', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'billing_month', name='uq_user_billing_month'),
    )
    op.create_index('idx_monthly_usages_user_month', 'monthly_usages', ['user_id', 'billing_month'])


def downgrade() -> None:
    op.drop_table('monthly_usages')
    op.drop_table('evaluation_results')
    op.drop_table('assignment_folders')
