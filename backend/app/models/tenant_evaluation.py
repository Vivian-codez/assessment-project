"""Multi-tenant, user-scoped AI assignment evaluation models.

Exports:
- User
- AssignmentFolder
- FolderSubmission
- Submission (alias to FolderSubmission)
- EvaluationResult
- MonthlyUsage
"""

from app.models.user import User
from app.models.assignment_folder import (
    AssignmentFolder,
    FolderSubmission,
    Submission,
    EvaluationResult,
    MonthlyUsage,
)

__all__ = [
    "User",
    "AssignmentFolder",
    "FolderSubmission",
    "Submission",
    "EvaluationResult",
    "MonthlyUsage",
]
