# Module docstring explaining authentication, user signup/signin, profile, and preference endpoints
"""Authentication, User Sign-Up/Sign-In, Profile & Preferences API endpoints.

Refactored to use standard, self-contained JWT authentication with direct
PostgreSQL persistence via SQLAlchemy, fully decoupled from Supabase Auth.
"""

# Import uuid library to generate cryptographically unique random identifiers for entities
import uuid
# Import datetime, timedelta, and timezone from datetime module for UTC timestamps and expiration calculations
from datetime import datetime, timedelta, timezone
# Import Optional type annotation for nullable function parameters and variables
from typing import Optional
# Import FastAPI core routing, dependency injection, HTTP exceptions, status codes, and request objects
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request
# Import Session class from SQLAlchemy ORM for database transaction management
from sqlalchemy.orm import Session

# Import application settings singleton containing configuration constants
from app.core.config import settings
# Import database session dependency injector for yielding database connections
from app.core.database import get_db
# Import cryptographic password hashing, verification, and JWT generation/decoding utilities
from app.core.security import (
    # Function to verify plaintext password against stored cryptographic hash
    verify_password,
    # Function to hash plaintext password using bcrypt with 12 rounds
    get_password_hash,
    # Function to generate signed JWT access tokens
    create_access_token,
    # Function to decode and validate JWT access tokens
    decode_access_token,
    # OAuth2 password bearer scheme instance for extracting bearer tokens
    oauth2_scheme,
)
# Import application logger for logging diagnostic messages
from app.core.logging import logger
# Import User and UserSession SQLAlchemy database models
from app.models.user import User, UserSession
# Import Instructor SQLAlchemy database model for instructional relation mapping
from app.models.instructor import Instructor
# Import Course SQLAlchemy database model for course management
from app.models.course import Course
# Import Pydantic validation schemas for authentication request and response serialization
from app.schemas.auth import (
    # Schema validating user registration payload
    UserSignUp,
    # Schema validating user login credentials payload
    UserLogin,
    # Schema serializing user profile response data
    UserResponse,
    # Schema validating educator preference update payloads
    TeacherPreferencesUpdate,
    # Schema serializing combined token and user profile responses
    AuthResponse,
)

# Initialize FastAPI API router instance for authentication and profile routes with prefix /auth
router = APIRouter(prefix="/auth", tags=["Authentication & Profile"])


# Authentication dependency resolving authenticated User model from Bearer token
def get_current_user(
    # Extract access token string via OAuth2 password bearer dependency
    token: Optional[str] = Depends(oauth2_scheme),
    # Optional raw Authorization header string fallback
    authorization: Optional[str] = Header(None),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
) -> User:
    # Function docstring explaining user resolution behavior
    """Authenticates request via JWT access token and returns PostgreSQL User.

    Extracts token from OAuth2 Bearer scheme or Authorization header,
    validates the signature and expiration using local SECRET_KEY/HS256,
    and retrieves the user record from the local database.
    """
    # Assign extracted OAuth2 token to local variable
    raw_token = token
    # Check if raw token is missing but Authorization header starts with Bearer prefix
    if not raw_token and authorization and authorization.startswith("Bearer "):
        # Extract token substring following the Bearer prefix and strip whitespace
        raw_token = authorization.split(" ")[1].strip()

    # Check if no token was resolved from either source
    if not raw_token:
        # Raise HTTP 401 Unauthorized exception requiring valid credentials
        raise HTTPException(
            # Specify HTTP 401 status code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Provide descriptive error explanation message
            detail="Authentication required. Please provide a valid Bearer token.",
            # Include WWW-Authenticate header with Bearer realm
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Decode and verify JWT token payload using secret key and HS256 algorithm
    payload = decode_access_token(raw_token)
    # Validate that payload is a non-empty dictionary
    if not payload or not isinstance(payload, dict):
        # Raise HTTP 401 Unauthorized exception for invalid or expired token
        raise HTTPException(
            # Specify HTTP 401 status code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Provide descriptive message to prompt re-authentication
            detail="Invalid or expired authentication token. Please sign in again.",
            # Include WWW-Authenticate header with Bearer realm
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Extract user identifier from token subject claim
    user_id = payload.get("sub")
    # Verify that subject claim exists in decoded token payload
    if not user_id:
        # Raise HTTP 401 Unauthorized exception for malformed token
        raise HTTPException(
            # Specify HTTP 401 status code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Provide error explanation
            detail="Token payload missing subject identifier.",
            # Include WWW-Authenticate header with Bearer realm
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check session revocation / invalidation status in database
    session = db.query(UserSession).filter(UserSession.token == raw_token).first()
    if session and session.expires_at:
        now_dt = datetime.now(timezone.utc).replace(tzinfo=None)
        expires_dt = session.expires_at if session.expires_at.tzinfo is None else session.expires_at.replace(tzinfo=None)
        if expires_dt < now_dt:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session has been terminated. Please sign in again.",
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Query PostgreSQL User table matching either user id or email address
    user = db.query(User).filter((User.id == str(user_id)) | (User.email == str(user_id))).first()
    # Check if user record was not found in users table
    if not user:
        # Check if legacy instructor record exists with this id or email
        instructor = db.query(Instructor).filter((Instructor.id == str(user_id)) | (Instructor.email == str(user_id))).first()
        # Check if matching instructor record was found
        if instructor:
            # Instantiate new User record mirroring instructor data
            user = User(
                # Mirror instructor id as user primary key
                id=instructor.id,
                # Mirror instructor display name
                name=instructor.name,
                # Mirror full name attribute
                full_name=instructor.name,
                # Mirror email address
                email=instructor.email,
                # Mirror user role
                role=instructor.role,
                # Mirror password hash
                hashed_password=instructor.hashed_password,
                # Mirror existing preference dictionary or default to empty dict
                preferences=instructor.preferences or {},
            )
            # Stage new user entity into database session
            db.add(user)
            # Commit transaction to persist user record to PostgreSQL
            db.commit()
            # Refresh user instance to load generated timestamps
            db.refresh(user)
        # Handle case where neither user nor instructor record exists
        else:
            # Raise HTTP 401 Unauthorized indicating user does not exist
            raise HTTPException(
                # Specify HTTP 401 status code
                status_code=status.HTTP_401_UNAUTHORIZED,
                # Provide descriptive error detail message
                detail="User account not found or deactivated.",
                # Include WWW-Authenticate header with Bearer realm
                headers={"WWW-Authenticate": "Bearer"},
            )

    # Return authenticated User database model instance
    return user


# Relational dependency resolving or synchronizing Instructor model from authenticated User
def get_current_instructor(
    # Resolve authenticated User entity from get_current_user dependency
    user: User = Depends(get_current_user),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
) -> Instructor:
    # Function docstring explaining instructor resolution behavior
    """Dependency that returns the current Instructor model for course/grading relations."""
    # Query database for Instructor record matching user id or email
    instructor = db.query(Instructor).filter((Instructor.id == user.id) | (Instructor.email == user.email)).first()
    # Check if corresponding Instructor record does not exist
    if not instructor:
        # Compute display name from full_name, name, or capitalized email username prefix
        display_name = user.full_name or user.name or user.email.split("@")[0].capitalize()
        # Instantiate new Instructor entity mirroring user attributes
        instructor = Instructor(
            # Assign user id as instructor identifier
            id=user.id,
            # Assign resolved display name
            name=display_name,
            # Assign user email address
            email=user.email,
            # Assign user academic role
            role=user.role,
            # Mirror hashed password
            hashed_password=user.hashed_password,
            # Mirror user preferences or default to empty dictionary
            preferences=user.preferences or {},
        )
        # Stage new instructor record in database session
        db.add(instructor)
        # Commit transaction to PostgreSQL database
        db.commit()
        # Refresh instructor instance from database
        db.refresh(instructor)
    # Return resolved Instructor database model instance
    return instructor


# HTTP POST route handler for registering new user accounts
@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def sign_up(
    # Validate incoming JSON registration payload using UserSignUp schema
    signup_data: UserSignUp,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing signup functionality
    """Register a new user account with direct PostgreSQL persistence and issue JWT."""
    # Clean, normalize, and lowercase registration email address
    email_clean = signup_data.email.lower().strip()
    # Check if an existing user already exists with this email address
    existing_user = db.query(User).filter(User.email == email_clean).first()
    # Check if query returned an existing user
    if existing_user:
        # Raise HTTP 400 Bad Request exception to prevent duplicate accounts
        raise HTTPException(
            # Specify HTTP 400 status code
            status_code=status.HTTP_400_BAD_REQUEST,
            # Return human-readable message instructing user to sign in
            detail="An account with this email address already exists. Please sign in.",
        )

    # Resolve display name from full_name or legacy name field
    display_name = (signup_data.full_name or signup_data.name or "").strip()
    # Fallback to email username prefix if display name is empty
    if not display_name:
        # Capitalize email username prefix as fallback name
        display_name = email_clean.split("@")[0].capitalize()

    # Generate cryptographically unique UUID string identifier for new user
    user_id = str(uuid.uuid4())
    # Hash plaintext password using bcrypt with 12 rounds
    hashed_pwd = get_password_hash(signup_data.password)
    # Define default educator UI and grading preferences dictionary
    default_prefs = {
        # Enable showing similarity context cards by default
        "show_similarity_context": True,
        # Do not require mandatory notes for score overrides by default
        "require_teacher_notes_on_overrides": False,
        # Enable displaying AI content indicator probability flag
        "include_ai_content_indicator": True,
    }

    # Instantiate new User model instance with sanitized user credentials
    new_user = User(
        # Set generated unique user UUID
        id=user_id,
        # Set full name attribute
        full_name=display_name,
        # Set legacy name attribute
        name=display_name,
        # Set validated email address
        email=email_clean,
        # Set academic role or fallback to default Computer Science title
        role=signup_data.role or "Instructor · Computer Science",
        # Set securely hashed bcrypt password
        hashed_password=hashed_pwd,
        # Set default educator preferences dictionary
        preferences=default_prefs,
    )
    # Stage new user entity into database session
    db.add(new_user)

    # Mirror as Instructor entity to satisfy foreign key relationships in courses and assignments
    new_instructor = Instructor(
        # Match instructor primary key with user id
        id=user_id,
        # Set instructor display name
        name=display_name,
        # Set instructor email address
        email=email_clean,
        # Set instructor academic role
        role=signup_data.role or "Instructor · Computer Science",
        # Set securely hashed bcrypt password
        hashed_password=hashed_pwd,
        # Set default educator preferences dictionary
        preferences=default_prefs,
    )
    # Stage new instructor entity into database session
    db.add(new_instructor)
    # Commit transaction to PostgreSQL database
    db.commit()
    # Refresh new_user instance to populate database default fields
    db.refresh(new_user)

    # Generate signed JWT Bearer access token containing user id in sub claim
    token = create_access_token({"sub": str(new_user.id)})
    # Generate unique alphanumeric session identifier
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    # Calculate session expiration datetime in UTC
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Instantiate UserSession entity to track active login session in PostgreSQL
    user_session = UserSession(
        # Set unique session identifier
        id=session_id,
        # Link session to newly created user id
        user_id=new_user.id,
        # Store issued JWT access token string
        token=token,
        # Store absolute expiration timestamp
        expires_at=expires,
    )
    # Stage new session entity into database session
    db.add(user_session)
    # Commit session transaction to PostgreSQL database
    db.commit()

    # Construct serialized UserResponse schema representation
    user_resp = UserResponse(
        # Convert user id to string
        id=str(new_user.id),
        # Set display name
        name=display_name,
        # Set full name
        full_name=display_name,
        # Set email address
        email=new_user.email,
        # Set academic role
        role=new_user.role,
        # Return user preferences dictionary or fallback to defaults
        preferences=new_user.preferences or default_prefs,
    )
    # Return AuthResponse containing issued JWT access token and user profile
    return AuthResponse(access_token=token, token_type="bearer", user=user_resp)


# HTTP POST route handler for authenticating existing users and issuing JWT tokens
@router.post("/login", response_model=AuthResponse)
async def login(
    # Inject FastAPI raw Request object to handle JSON and form data uniformly
    request: Request,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing login credentials processing
    """Authenticate credentials via PostgreSQL and issue standard JWT Bearer token.

    Accepts both JSON payloads (`{ "email": "...", "password": "..." }`) and
    standard OAuth2 password form data (`username` and `password`).
    """
    # Extract Content-Type header string from incoming HTTP request
    content_type = request.headers.get("content-type", "")
    # Initialize email variable to None
    email = None
    # Initialize password variable to None
    password = None

    # Check if incoming request body is formatted as JSON
    if "application/json" in content_type:
        # Wrap JSON parsing in try block to handle malformed JSON bodies gracefully
        try:
            # Asynchronously parse incoming JSON request body dictionary
            body = await request.json()
            # Extract email or username key from parsed JSON dictionary
            email = body.get("email") or body.get("username")
            # Extract password string from parsed JSON dictionary
            password = body.get("password")
        # Catch JSON decoding errors
        except Exception:
            # Pass to allow fallback checks
            pass
    # Check if incoming request body is formatted as URL-encoded or multipart form data
    elif "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        # Wrap form parsing in try block
        try:
            # Asynchronously parse form data fields
            form = await request.form()
            # Extract username or email field from form data
            email = form.get("username") or form.get("email")
            # Extract password field from form data
            password = form.get("password")
        # Catch form parsing exceptions
        except Exception:
            # Pass to allow fallback checks
            pass
    # Handle requests with missing or alternative content-type headers
    else:
        # Attempt fallback JSON parsing first
        try:
            # Parse body as JSON
            body = await request.json()
            # Extract email or username
            email = body.get("email") or body.get("username")
            # Extract password
            password = body.get("password")
        # Handle non-JSON payload fallback
        except Exception:
            # Attempt fallback form data parsing
            try:
                # Parse body as form data
                form = await request.form()
                # Extract username or email
                email = form.get("username") or form.get("email")
                # Extract password
                password = form.get("password")
            # Catch all parsing exceptions
            except Exception:
                # Pass gracefully
                pass

    # Validate that both email and password were provided
    if not email or not password:
        # Raise HTTP 400 Bad Request exception for missing credentials
        raise HTTPException(
            # Specify HTTP 400 status code
            status_code=status.HTTP_400_BAD_REQUEST,
            # Provide error detail message
            detail="Email and password credentials are required.",
        )

    # Normalize, clean, and lowercase provided email address string
    email_clean = str(email).lower().strip()
    # Query PostgreSQL User table matching cleaned email address
    user = db.query(User).filter(User.email == email_clean).first()
    # Query PostgreSQL Instructor table matching cleaned email address
    instructor = db.query(Instructor).filter(Instructor.email == email_clean).first()

    # Identify primary matched database record from user or instructor tables
    matched_record = user or instructor
    # Verify that matched record exists and plain password matches stored bcrypt hash
    if not matched_record or not verify_password(str(password), matched_record.hashed_password):
        # Raise HTTP 401 Unauthorized exception on credential mismatch
        raise HTTPException(
            # Specify HTTP 401 status code
            status_code=status.HTTP_401_UNAUTHORIZED,
            # Provide security error detail message
            detail="Invalid email or password. Please verify your credentials.",
            # Include WWW-Authenticate header with Bearer realm
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Check if user record exists without a corresponding instructor record
    if user and not instructor:
        # Compute display name from user attributes
        display_name = user.full_name or user.name or user.email.split("@")[0].capitalize()
        # Instantiate mirrored Instructor record
        instructor = Instructor(
            # Mirror user id
            id=user.id,
            # Mirror display name
            name=display_name,
            # Mirror email address
            email=user.email,
            # Mirror academic role
            role=user.role,
            # Mirror hashed password
            hashed_password=user.hashed_password,
            # Mirror preferences or default to empty dict
            preferences=user.preferences or {},
        )
        # Stage new instructor record into database session
        db.add(instructor)
        # Commit transaction to PostgreSQL
        db.commit()
    # Check if instructor record exists without a corresponding user record
    elif instructor and not user:
        # Instantiate mirrored User record
        user = User(
            # Mirror instructor id
            id=instructor.id,
            # Mirror name
            name=instructor.name,
            # Mirror full name
            full_name=instructor.name,
            # Mirror email address
            email=instructor.email,
            # Mirror academic role
            role=instructor.role,
            # Mirror hashed password
            hashed_password=instructor.hashed_password,
            # Mirror preferences or default to empty dict
            preferences=instructor.preferences or {},
        )
        # Stage new user record into database session
        db.add(user)
        # Commit transaction to PostgreSQL
        db.commit()

    # Generate signed JWT Bearer access token containing authenticated user id
    token = create_access_token({"sub": str(matched_record.id)})
    # Generate unique alphanumeric session identifier
    session_id = f"sess_{uuid.uuid4().hex[:12]}"
    # Calculate session expiration datetime in UTC
    expires = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    # Instantiate UserSession record to track active session
    user_session = UserSession(
        # Set session identifier
        id=session_id,
        # Link session to matched user id
        user_id=matched_record.id,
        # Store issued JWT access token string
        token=token,
        # Store expiration timestamp
        expires_at=expires,
    )
    # Stage new session entity into database session
    db.add(user_session)
    # Commit session transaction to PostgreSQL
    db.commit()

    # Resolve display name across user, instructor, and email fallback
    display_name = (
        # Check user full_name attribute
        getattr(user, "full_name", None)
        # Check user name attribute
        or getattr(user, "name", None)
        # Check instructor name attribute
        or getattr(matched_record, "name", "")
        # Fallback to capitalized email prefix
        or email_clean.split("@")[0].capitalize()
    )
    # Construct serialized UserResponse schema representation
    user_resp = UserResponse(
        # Convert user id to string
        id=str(matched_record.id),
        # Set display name
        name=display_name,
        # Set full name
        full_name=display_name,
        # Set email address
        email=matched_record.email,
        # Set academic role
        role=matched_record.role,
        # Retrieve user preferences or default to empty dictionary
        preferences=getattr(matched_record, "preferences", {}) or {},
    )
    # Return AuthResponse containing issued JWT access token and user profile
    return AuthResponse(access_token=token, token_type="bearer", user=user_resp)


# HTTP GET route handler returning currently authenticated user profile
@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    # Resolve authenticated user entity from get_current_user dependency
    current_user: User = Depends(get_current_user),
):
    # Route docstring describing profile retrieval functionality
    """Retrieve the current logged-in user's profile and UI preferences."""
    # Resolve user display name from full_name, name, or email prefix
    display_name = current_user.full_name or current_user.name or current_user.email.split("@")[0].capitalize()
    # Construct and return UserResponse schema representation
    return UserResponse(
        # Convert user id to string
        id=str(current_user.id),
        # Set display name
        name=display_name,
        # Set full name
        full_name=display_name,
        # Set email address
        email=current_user.email,
        # Set academic role
        role=current_user.role,
        # Set user UI preferences dictionary
        preferences=current_user.preferences or {},
    )


# HTTP PUT route handler updating educator profile settings and UI preferences
@router.put("/preferences", response_model=UserResponse)
def update_preferences(
    # Validate incoming preferences update payload using TeacherPreferencesUpdate schema
    payload: TeacherPreferencesUpdate,
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Resolve currently authenticated user dependency
    current_user: User = Depends(get_current_user),
):
    # Route docstring describing preference update functionality
    """Update user review preferences and profile settings in PostgreSQL."""
    # Extract updated display name from full_name or name fields
    display_name = payload.full_name or payload.name
    # Check if a new display name was provided in the update payload
    if display_name:
        # Update user name attribute
        current_user.name = display_name
        # Update user full_name attribute
        current_user.full_name = display_name
    # Check if a new academic role was provided in the update payload
    if payload.role:
        # Update user role attribute
        current_user.role = payload.role

    # Create shallow copy of current preferences dictionary or initialize new dictionary
    prefs = dict(current_user.preferences or {})
    # Check if show_similarity_context flag was updated
    if payload.show_similarity_context is not None:
        # Update preference flag in dictionary
        prefs["show_similarity_context"] = payload.show_similarity_context
    # Check if require_teacher_notes_on_overrides flag was updated
    if payload.require_teacher_notes_on_overrides is not None:
        # Update preference flag in dictionary
        prefs["require_teacher_notes_on_overrides"] = payload.require_teacher_notes_on_overrides
    # Check if include_ai_content_indicator flag was updated
    if payload.include_ai_content_indicator is not None:
        # Update preference flag in dictionary
        prefs["include_ai_content_indicator"] = payload.include_ai_content_indicator

    # Persist updated preferences dictionary to User model instance
    current_user.preferences = prefs

    # Query matching Instructor entity to maintain synchronicity
    instructor = db.query(Instructor).filter(Instructor.id == current_user.id).first()
    # Check if matching instructor record exists in database
    if instructor:
        # Synchronize preferences to instructor record
        instructor.preferences = prefs
        # Check if display name was changed
        if display_name:
            # Update instructor name attribute
            instructor.name = display_name
        # Check if role was changed
        if payload.role:
            # Update instructor role attribute
            instructor.role = payload.role

    # Commit all pending attribute modifications to PostgreSQL
    db.commit()
    # Refresh current user model instance from database
    db.refresh(current_user)

    # Determine final response display name string
    res_name = current_user.full_name or current_user.name or ""
    # Construct and return updated UserResponse schema representation
    return UserResponse(
        # Convert user id to string
        id=str(current_user.id),
        # Set display name
        name=res_name,
        # Set full name
        full_name=res_name,
        # Set email address
        email=current_user.email,
        # Set academic role
        role=current_user.role,
        # Set updated preferences dictionary
        preferences=current_user.preferences or {},
    )


# HTTP POST route handler for revoking user session tokens upon sign out
@router.post("/logout")
def logout(
    # Optional raw Authorization header string
    authorization: Optional[str] = Header(None),
    # Optional token resolved from OAuth2 password bearer scheme
    token: Optional[str] = Depends(oauth2_scheme),
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
):
    # Route docstring describing logout functionality
    """Log out user and invalidate current session in PostgreSQL."""
    # Assign extracted OAuth2 token
    raw_token = token
    # Fallback to Authorization header if OAuth2 token was omitted
    if not raw_token and authorization and authorization.startswith("Bearer "):
        # Extract bearer token substring
        raw_token = authorization.split(" ")[1].strip()

    # Check if a valid token string was resolved
    if raw_token:
        # Invalidate active UserSession in database by terminating its validity timestamp
        past_time = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=1)
        session = db.query(UserSession).filter(UserSession.token == raw_token).first()
        if session:
            session.expires_at = past_time
            db.commit()
            logger.info(f"[AUTH] Invalided active session token {raw_token[:10]}... upon explicit user logout.")
        else:
            try:
                payload = decode_access_token(raw_token)
                sub = payload.get("sub", "unknown") if payload else "unknown"
            except Exception:
                sub = "unknown"
            revoked_session = UserSession(
                id=str(uuid.uuid4()),
                user_id=str(sub),
                token=raw_token,
                expires_at=past_time,
            )
            db.add(revoked_session)
            db.commit()
            logger.info(f"[AUTH] Created revoked session entry for token {raw_token[:10]}... upon explicit logout.")
    # Return success confirmation response dictionary
    return {"message": "Signed out successfully. Session invalidated."}


# HTTP POST route handler for purging demo mock courses from test accounts
@router.post("/clear-mock-data")
def clear_mock_data(
    # Inject active SQLAlchemy database session dependency
    db: Session = Depends(get_db),
    # Require authentication dependency to protect endpoint
    current_user: User = Depends(get_current_user),
):
    # Route docstring describing mock data purge behavior
    """Purge seeded sample mock courses and submissions from database."""
    # Query all courses belonging to mock instructor ID inst_priya_rao
    mock_courses = db.query(Course).filter(Course.instructor_id == "inst_priya_rao").all()
    # Count total number of mock courses found
    count = len(mock_courses)
    # Iterate through each mock course entity
    for c in mock_courses:
        # Delete mock course from database session
        db.delete(c)
    # Commit deletion transaction to PostgreSQL
    db.commit()

    # Return confirmation dictionary with count of purged records
    return {"message": f"Successfully removed {count} mock courses and associated records."}
