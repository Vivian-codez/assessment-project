"""Authentication, User Sign-Up/Sign-In, Profile & Preferences API endpoints.

Refactored to use standard, self-contained JWT authentication with direct
PostgreSQL persistence via SQLAlchemy, fully decoupled from Supabase Auth.
"""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token,
    decode_access_token,
    oauth2_scheme,
)
from app.core.logging import logger
from app.models.user import User, UserSession
from app.models.instructor import Instructor
from app.models.course import Course
from app.schemas.auth import (
    UserSignUp,
    UserLogin,
    UserResponse,
    TeacherPreferencesUpdate,
    AuthResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> User:
    """Authenticates request via JWT access token and returns PostgreSQL User.

    Extracts token from OAuth2 Bearer scheme or Authorization header,
    validates the signature and expiration using local SECRET_KEY/HS256,
    and retrieves the user record from the local database.
    """
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1].strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(raw_token)
    if not payload or not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing subject identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter((User.id == str(user_id)) | (User.email == str(user_id))).first()
    if not user:
        # Check if user exists in legacy Instructor table and synchronize to User
        instructor = db.query(Instructor).filter((Instructor.id == str(user_id)) | (Instructor.email == str(user_id))).first()
        if instructor:
            user = User(
                id=instructor.id,
                name=instructor.name,
                full_name=instructor.name,
                email=instructor.email,
                role=instructor.role,
                hashed_password=instructor.hashed_password,
                preferences=instructor.preferences or {},
            )
            db.add(user)
            db.commit()
            db.refresh(user)
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account not found or deactivated.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    return user


def get_current_instructor(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Instructor:
    """Dependency that returns the current Instructor model for course/grading relations."""
    instructor = db.query(Instructor).filter((Instructor.id == user.id) | (Instructor.email == user.email)).first()
    if not instructor:
        display_name = user.full_name or user.name or user.email.split("@")[0].capitalize()
        instructor = Instructor(
            id=user.id,
            name=display_name,
            email=user.email,
            role=user.role,
            hashed_password=user.hashed_password,
            preferences=user.preferences or {},
        )
        db.add(instructor)
        db.commit()
        db.refresh(instructor)
    return instructor


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def sign_up(
    signup_data: UserSignUp,
    db: Session = Depends(get_db),
):
    """Register a new user account with direct PostgreSQL persistence and issue JWT."""
    email_clean = signup_data.email.lower().strip()
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in.",
        )

    display_name = (signup_data.full_name or signup_data.name or "").strip()
    if not display_name:
        display_name = email_clean.split("@")[0].capitalize()

    user_id = str(uuid.uuid4())
    hashed_pwd = get_password_hash(signup_data.password)
    default_prefs = {
        "show_similarity_context": True,
        "require_teacher_notes_on_overrides": False,
        "include_ai_content_indicator": True,
    }

    new_user = User(
        id=user_id,
        full_name=display_name,
        name=display_name,
        email=email_clean,
        role=signup_data.role or "Instructor · Computer Science",
        hashed_password=hashed_pwd,
        preferences=default_prefs,
    )
    db.add(new_user)

    # Mirror as Instructor for course relational foreign keys
    new_instructor = Instructor(
        id=user_id,
        name=display_name,
        email=email_clean,
        role=signup_data.role or "Instructor · Computer Science",
        hashed_password=hashed_pwd,
        preferences=default_prefs,
    )
    db.add(new_instructor)
    db.commit()
    db.refresh(new_user)

    token = create_access_token({"sub": str(new_user.id)})
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_session = UserSession(
        id=session_id,
        user_id=new_user.id,
        token=token,
        expires_at=expires,
    )
    db.add(user_session)
    db.commit()

    user_resp = UserResponse(
        id=str(new_user.id),
        name=display_name,
        full_name=display_name,
        email=new_user.email,
        role=new_user.role,
        preferences=new_user.preferences or default_prefs,
    )
    return AuthResponse(access_token=token, token_type="bearer", user=user_resp)


@router.post("/login", response_model=AuthResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
):
    """Authenticate credentials via PostgreSQL and issue standard JWT Bearer token.

    Accepts both JSON payloads (`{ "email": "...", "password": "..." }`) and
    standard OAuth2 password form data (`username` and `password`).
    """
    content_type = request.headers.get("content-type", "")
    email = None
    password = None

    if "application/json" in content_type:
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            pass
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        try:
            form = await request.form()
            email = form.get("username") or form.get("email")
            password = form.get("password")
        except Exception:
            pass
    else:
        # Fallback attempt json then form
        try:
            body = await request.json()
            email = body.get("email") or body.get("username")
            password = body.get("password")
        except Exception:
            try:
                form = await request.form()
                email = form.get("username") or form.get("email")
                password = form.get("password")
            except Exception:
                pass

    if not email or not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email and password credentials are required.",
        )

    email_clean = str(email).lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    instructor = db.query(Instructor).filter(Instructor.email == email_clean).first()

    matched_record = user or instructor
    if not matched_record or not verify_password(str(password), matched_record.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Ensure synchronization between user and instructor records
    if user and not instructor:
        display_name = user.full_name or user.name or user.email.split("@")[0].capitalize()
        instructor = Instructor(
            id=user.id,
            name=display_name,
            email=user.email,
            role=user.role,
            hashed_password=user.hashed_password,
            preferences=user.preferences or {},
        )
        db.add(instructor)
        db.commit()
    elif instructor and not user:
        user = User(
            id=instructor.id,
            name=instructor.name,
            full_name=instructor.name,
            email=instructor.email,
            role=instructor.role,
            hashed_password=instructor.hashed_password,
            preferences=instructor.preferences or {},
        )
        db.add(user)
        db.commit()

    token = create_access_token({"sub": str(matched_record.id)})
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    user_session = UserSession(
        id=session_id,
        user_id=matched_record.id,
        token=token,
        expires_at=expires,
    )
    db.add(user_session)
    db.commit()

    display_name = (
        getattr(user, "full_name", None)
        or getattr(user, "name", None)
        or getattr(matched_record, "name", "")
        or email_clean.split("@")[0].capitalize()
    )
    user_resp = UserResponse(
        id=str(matched_record.id),
        name=display_name,
        full_name=display_name,
        email=matched_record.email,
        role=matched_record.role,
        preferences=getattr(matched_record, "preferences", {}) or {},
    )
    return AuthResponse(access_token=token, token_type="bearer", user=user_resp)


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve the current logged-in user's profile and UI preferences."""
    display_name = current_user.full_name or current_user.name or current_user.email.split("@")[0].capitalize()
    return UserResponse(
        id=str(current_user.id),
        name=display_name,
        full_name=display_name,
        email=current_user.email,
        role=current_user.role,
        preferences=current_user.preferences or {},
    )


@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    payload: TeacherPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update user review preferences and profile settings in PostgreSQL."""
    display_name = payload.full_name or payload.name
    if display_name:
        current_user.name = display_name
        current_user.full_name = display_name
    if payload.role:
        current_user.role = payload.role

    prefs = dict(current_user.preferences or {})
    if payload.show_similarity_context is not None:
        prefs["show_similarity_context"] = payload.show_similarity_context
    if payload.require_teacher_notes_on_overrides is not None:
        prefs["require_teacher_notes_on_overrides"] = payload.require_teacher_notes_on_overrides
    if payload.include_ai_content_indicator is not None:
        prefs["include_ai_content_indicator"] = payload.include_ai_content_indicator

    current_user.preferences = prefs

    # Sync to Instructor record
    instructor = db.query(Instructor).filter(Instructor.id == current_user.id).first()
    if instructor:
        instructor.preferences = prefs
        if display_name:
            instructor.name = display_name
        if payload.role:
            instructor.role = payload.role

    db.commit()
    db.refresh(current_user)

    res_name = current_user.full_name or current_user.name or ""
    return UserResponse(
        id=str(current_user.id),
        name=res_name,
        full_name=res_name,
        email=current_user.email,
        role=current_user.role,
        preferences=current_user.preferences or {},
    )


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Log out user and invalidate current session in PostgreSQL."""
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split(" ")[1].strip()

    if raw_token:
        db.query(UserSession).filter(UserSession.token == raw_token).delete()
        db.commit()
    return {"message": "Signed out successfully."}


@router.post("/clear-mock-data")
def clear_mock_data(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Purge seeded sample mock courses and submissions from database."""
    mock_courses = db.query(Course).filter(Course.instructor_id == "inst_priya_rao").all()
    count = len(mock_courses)
    for c in mock_courses:
        db.delete(c)
    db.commit()

    return {"message": f"Successfully removed {count} mock courses and associated records."}

