# Module docstring explaining reusable FastAPI dependency injectors for multi-tenant isolation
"""Reusable FastAPI dependencies for multi-tenant authentication and scope isolation."""

# Import FastAPI dependency, HTTP exception, and status primitives
from fastapi import Depends, HTTPException, status
# Import SQLAlchemy Session class
from sqlalchemy.orm import Session

# Import database session provider
from app.core.database import get_db
# Import User, AssignmentFolder, Course, and Classroom models
from app.models.user import User
from app.models.assignment_folder import AssignmentFolder
from app.models.course import Course
from app.models.classroom import Classroom
# Import get_current_user and role dependencies
from app.api.v1.auth import get_current_user, require_teacher, require_admin


# Dependency verifying that the requested assignment folder belongs to current_user
def get_user_scoped_folder(
    folder_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AssignmentFolder:
    """Enforces strict tenant isolation by verifying the folder belongs to current_user.

    Raises HTTP 404 if the folder does not exist or belongs to another tenant.
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


# Dependency verifying that the requested course belongs to current_user or permitted scope
def get_user_scoped_course(
    course_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Course:
    """Enforces strict tenant isolation by verifying the course belongs to current_user."""
    course = (
        db.query(Course)
        .filter(
            Course.id == str(course_id),
            (
                (Course.user_id == str(current_user.id))
                | (Course.instructor_id == str(current_user.id))
                | (Course.user_id.is_(None))
            ),
        )
        .first()
    )
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found or access denied.",
        )
    return course


# Dependency verifying that the requested classroom belongs to current_user
def get_user_scoped_classroom(
    classroom_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Classroom:
    """Enforces strict tenant isolation by verifying the classroom belongs to current_user."""
    classroom = (
        db.query(Classroom)
        .filter(
            Classroom.id == str(classroom_id),
            (
                (Classroom.instructor_id == str(current_user.id))
                | (Classroom.instructor_id.is_(None))
            ),
        )
        .first()
    )
    if not classroom:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Classroom not found or access denied.",
        )
    return classroom
