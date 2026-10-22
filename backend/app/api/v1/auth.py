"""Authentication, User Sign-Up/Sign-In, Profile & Preferences API endpoints."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.core.logging import logger
from app.models.user import User, UserSession
from app.models.instructor import Instructor
from app.models.course import Course
from app.schemas.auth import (
    UserSignUp,
    UserLogin,
    InstructorLogin,
    UserResponse,
    InstructorResponse,
    TeacherPreferencesUpdate,
    AuthResponse,
    Token,
)
from app.core.supabase import supabase

router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


def get_current_instructor(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
) -> Instructor:
    """Returns authenticated user from Bearer token via Supabase Auth or local JWT.
    
    Raises 401 if unauthenticated. No hardcoded or demo fallbacks.
    """
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]

        # 1. First check with Supabase Auth
        try:
            sb_user_res = supabase.auth.get_user(token)
            if sb_user_res and sb_user_res.user:
                sb_u = sb_user_res.user
                inst_id = str(sb_u.id)
                inst = db.query(Instructor).filter(Instructor.id == inst_id).first()
                user_meta = sb_u.user_metadata or {}
                name = user_meta.get("name") or user_meta.get("full_name") or (sb_u.email.split("@")[0] if sb_u.email else "Instructor")
                role = user_meta.get("role") or "Instructor · Computer Science"

                if not inst:
                    inst = Instructor(
                        id=inst_id,
                        name=name,
                        email=sb_u.email or f"{inst_id}@auth.supabase",
                        role=role,
                        hashed_password="supabase_auth_managed",
                        preferences={
                            "show_similarity_context": True,
                            "require_teacher_notes_on_overrides": False,
                            "include_ai_content_indicator": True,
                        },
                    )
                    db.add(inst)
                    db.commit()
                    db.refresh(inst)
                return inst
        except Exception as sb_err:
            logger.debug(f"Supabase auth check: {sb_err}")

        # 2. Check local JWT
        payload = decode_access_token(token)
        if payload and "sub" in payload:
            user_id = payload["sub"]
            instructor = db.query(Instructor).filter(Instructor.id == user_id).first()
            if instructor:
                return instructor
            user = db.query(User).filter(User.id == user_id).first()
            if user:
                inst = db.query(Instructor).filter(Instructor.email == user.email).first()
                if inst:
                    return inst
                new_inst = Instructor(
                    id=user.id,
                    name=user.name,
                    email=user.email,
                    role=user.role,
                    hashed_password=user.hashed_password,
                    preferences=user.preferences or {},
                )
                db.add(new_inst)
                db.commit()
                db.refresh(new_inst)
                return new_inst

    # Strict authentication guard: No fallback to Priya Rao
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please sign in with your email and password.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def sign_up(
    signup_data: UserSignUp,
    db: Session = Depends(get_db),
):
    """Register a new user account with Supabase and local PostgreSQL sync."""
    email_clean = signup_data.email.lower().strip()
    # Check if user already exists in PostgreSQL
    existing_user = db.query(User).filter(User.email == email_clean).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please sign in.",
        )

    user_id = f"usr_{uuid.uuid4().hex[:12]}"
    hashed_pwd = get_password_hash(signup_data.password)
    default_prefs = {
        "show_similarity_context": True,
        "require_teacher_notes_on_overrides": False,
        "include_ai_content_indicator": True,
    }

    # Create local User record
    new_user = User(
        id=user_id,
        name=signup_data.name.strip(),
        email=email_clean,
        role=signup_data.role or "Instructor · Computer Science",
        hashed_password=hashed_pwd,
        preferences=default_prefs,
    )
    db.add(new_user)

    # Also mirror as Instructor for course relational foreign keys
    new_instructor = Instructor(
        id=user_id,
        name=signup_data.name.strip(),
        email=email_clean,
        role=signup_data.role or "Instructor · Computer Science",
        hashed_password=hashed_pwd,
        preferences=default_prefs,
    )
    db.add(new_instructor)
    db.commit()
    db.refresh(new_user)

    # Sync to Supabase tables (public.users & public.instructors)
    try:
        supabase.table("users").upsert({
            "id": user_id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
            "hashed_password": hashed_pwd,
            "preferences": default_prefs,
        }).execute()

        supabase.table("instructors").upsert({
            "id": user_id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role,
            "hashed_password": hashed_pwd,
            "preferences": default_prefs,
        }).execute()
        logger.info(f"Synchronized new user {new_user.email} with Supabase authentication tables.")
    except Exception as e:
        logger.warning(f"Supabase user sync notice: {e}")

    token = create_access_token(new_user.id)
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

    try:
        supabase.table("user_sessions").insert({
            "id": session_id,
            "user_id": new_user.id,
            "token": token,
            "expires_at": expires.isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase user_sessions insert notice: {e}")

    user_resp = UserResponse(
        id=new_user.id,
        name=new_user.name,
        email=new_user.email,
        role=new_user.role,
        preferences=new_user.preferences or default_prefs,
    )
    return AuthResponse(access_token=token, token_type="bearer", user=user_resp)


@router.post("/login", response_model=AuthResponse)
def login(
    login_data: UserLogin,
    db: Session = Depends(get_db),
):
    """Authenticate existing user and issue JWT Bearer token."""
    email_clean = login_data.email.lower().strip()
    user = db.query(User).filter(User.email == email_clean).first()
    instructor = db.query(Instructor).filter(Instructor.email == email_clean).first()

    matched_record = user or instructor
    authenticated = False

    # 1. Authenticate via authentic Supabase Auth
    try:
        sb_auth = supabase.auth.sign_in_with_password({
            "email": email_clean,
            "password": login_data.password,
        })
        if sb_auth and sb_auth.user and sb_auth.session:
            sb_u = sb_auth.user
            token = sb_auth.session.access_token
            meta = sb_u.user_metadata or {}
            name = meta.get("name") or meta.get("full_name") or email_clean.split("@")[0]
            role = meta.get("role") or "Instructor · Computer Science"

            inst = db.query(Instructor).filter(Instructor.id == str(sb_u.id)).first()
            if not inst:
                inst = Instructor(
                    id=str(sb_u.id),
                    name=name,
                    email=sb_u.email or email_clean,
                    role=role,
                    hashed_password="supabase_auth_managed",
                    preferences={
                        "show_similarity_context": True,
                        "require_teacher_notes_on_overrides": False,
                        "include_ai_content_indicator": True,
                    },
                )
                db.add(inst)
                db.commit()
                db.refresh(inst)

            user_resp = UserResponse(
                id=str(sb_u.id),
                name=name,
                email=sb_u.email or email_clean,
                role=role,
                preferences=inst.preferences or {},
            )
            return AuthResponse(access_token=token, token_type="bearer", user=user_resp)
    except Exception as sb_err:
        logger.debug(f"Supabase sign_in_with_password notice: {sb_err}")

    # 2. Check local database credentials
    if matched_record and verify_password(login_data.password, matched_record.hashed_password):
        authenticated = True

    # 3. If not found locally, check Supabase users table
    if not authenticated:
        try:
            res = supabase.table("users").select("*").eq("email", email_clean).execute()
            if res.data and len(res.data) > 0:
                remote_user = res.data[0]
                if verify_password(login_data.password, remote_user.get("hashed_password", "")):
                    authenticated = True
                    matched_record = User(
                        id=remote_user["id"],
                        name=remote_user["name"],
                        email=remote_user["email"],
                        role=remote_user.get("role", "Instructor · Computer Science"),
                        hashed_password=remote_user["hashed_password"],
                        preferences=remote_user.get("preferences", {}),
                    )
                    db.add(matched_record)
                    db.commit()
        except Exception as e:
            logger.warning(f"Supabase login check notice: {e}")

    if not authenticated or not matched_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please verify your credentials.",
        )

    token = create_access_token(matched_record.id)
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

    try:
        supabase.table("user_sessions").insert({
            "id": session_id,
            "user_id": matched_record.id,
            "token": token,
            "expires_at": expires.isoformat(),
        }).execute()
    except Exception as e:
        logger.warning(f"Supabase user_sessions insert notice: {e}")

    user_resp = UserResponse(
        id=matched_record.id,
        name=matched_record.name,
        email=matched_record.email,
        role=matched_record.role,
        preferences=matched_record.preferences or {},
    )
    return AuthResponse(access_token=token, token_type="bearer", user=user_resp)


@router.post("/logout")
def logout(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Log out user and invalidate current session."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        db.query(UserSession).filter(UserSession.token == token).delete()
        db.commit()
        try:
            supabase.table("user_sessions").delete().eq("token", token).execute()
        except Exception as e:
            logger.warning(f"Supabase user_sessions delete notice: {e}")
    return {"message": "Signed out successfully."}



@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    current_instructor: Instructor = Depends(get_current_instructor),
):
    """Retrieve the current logged-in instructor's profile and UI preferences."""
    return UserResponse(
        id=current_instructor.id,
        name=current_instructor.name,
        email=current_instructor.email,
        role=current_instructor.role,
        preferences=current_instructor.preferences or {},
    )


@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    payload: TeacherPreferencesUpdate,
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Update instructor review preferences and profile settings."""
    if payload.name:
        instructor.name = payload.name
    if payload.role:
        instructor.role = payload.role

    prefs = dict(instructor.preferences or {})
    if payload.show_similarity_context is not None:
        prefs["show_similarity_context"] = payload.show_similarity_context
    if payload.require_teacher_notes_on_overrides is not None:
        prefs["require_teacher_notes_on_overrides"] = payload.require_teacher_notes_on_overrides
    if payload.include_ai_content_indicator is not None:
        prefs["include_ai_content_indicator"] = payload.include_ai_content_indicator

    instructor.preferences = prefs
    # Sync with User model if exists
    user = db.query(User).filter(User.id == instructor.id).first()
    if user:
        user.preferences = prefs
        if payload.name:
            user.name = payload.name
        if payload.role:
            user.role = payload.role

    db.commit()
    db.refresh(instructor)

    # Sync to Supabase
    try:
        supabase.table("users").update({"preferences": prefs}).eq("id", instructor.id).execute()
        supabase.table("instructors").update({"preferences": prefs}).eq("id", instructor.id).execute()
    except Exception as e:
        logger.warning(f"Supabase preferences sync notice: {e}")

    return UserResponse(
        id=instructor.id,
        name=instructor.name,
        email=instructor.email,
        role=instructor.role,
        preferences=instructor.preferences or {},
    )


@router.post("/clear-mock-data")
def clear_mock_data(
    db: Session = Depends(get_db),
    instructor: Instructor = Depends(get_current_instructor),
):
    """Purge seeded sample mock courses and submissions from database and Supabase."""
    mock_courses = db.query(Course).filter(Course.instructor_id == "inst_priya_rao").all()
    count = len(mock_courses)
    for c in mock_courses:
        db.delete(c)
    db.commit()

    try:
        supabase.table("courses").delete().eq("instructor_id", "inst_priya_rao").execute()
    except Exception as e:
        logger.warning(f"Supabase delete mock courses notice: {e}")

    return {"message": f"Successfully removed {count} mock courses and associated records."}

