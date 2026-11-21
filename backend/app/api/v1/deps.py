"""Reusable FastAPI dependencies for multi-tenant authentication and scope isolation."""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.user import User
from app.models.assignment_folder import AssignmentFolder
from app.api.v1.auth import get_current_user


def get_user_scoped_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssignmentFolder:
    """Enforces strict tenant isolation by verifying the folder belongs to current_user.

    Raises HTTP 404 (or 403) if the folder does not exist or belongs to another tenant.
    """
    folder = (
        db.query(AssignmentFolder)
        .filter(
            AssignmentFolder.id == str(folder_id),
            AssignmentFolder.user_id == str(current_user.id),
        )
        .first()
    )
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment folder not found or access denied.",
        )
    return folder

