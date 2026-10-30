# Module docstring explaining that this file defines authentication and user data models
"""Authentication and User schemas."""

# Import typing utilities for optional values and generic dictionary key-values
from typing import Optional, Dict, Any
# Import Pydantic base model, email validator, field constructor, and model configuration
from pydantic import BaseModel, EmailStr, Field, ConfigDict


# Schema for returning JWT access tokens upon successful authentication
class Token(BaseModel):
    # The JSON Web Token string issued to the client
    access_token: str
    # The authorization scheme used in the HTTP header, defaulting to bearer
    token_type: str = "bearer"


# Schema representing the decoded claims contained in a JWT token payload
class TokenPayload(BaseModel):
    # Subject claim representing the authenticated user's ID
    sub: Optional[str] = None
    # Expiration time claim as a UNIX epoch timestamp
    exp: Optional[int] = None


# Schema for validating user registration request payloads
class UserSignUp(BaseModel):
    # Full name of the user registering for an account
    full_name: Optional[str] = None
    name: Optional[str] = None
    # Validated email address of the registering user
    email: EmailStr
    # Raw plaintext password to be securely hashed upon creation
    password: str
    # User's functional title or role, defaulting to instructor
    role: Optional[str] = "Instructor · Computer Science"


# Schema for validating instructor login credentials
class InstructorLogin(BaseModel):
    # Validated email address used as the login identifier
    email: EmailStr
    # Plaintext password to verify against stored password hash
    password: str


# Schema for validating generic user login requests
class UserLogin(BaseModel):
    # Validated email address for authentication
    email: EmailStr
    # Plaintext password for authentication
    password: str


# Schema for updating customizable instructor preferences and settings
class TeacherPreferencesUpdate(BaseModel):
    # Optional updated full name for the instructor
    name: Optional[str] = None
    full_name: Optional[str] = None
    # Optional updated role or department description
    role: Optional[str] = None
    # Optional identifier of the default active course to display
    default_course: Optional[str] = None
    # Flag to toggle displaying similarity context cards in grading view
    show_similarity_context: Optional[bool] = None
    # Flag to require written justification when overriding automated scores
    require_teacher_notes_on_overrides: Optional[bool] = None
    # Flag to toggle indicators displaying detected AI content probability
    include_ai_content_indicator: Optional[bool] = None


# Schema for returning instructor profile information
class InstructorResponse(BaseModel):
    # Enable reading attributes directly from ORM database instances
    model_config = ConfigDict(from_attributes=True)

    # Unique string identifier of the instructor
    id: str
    # Full display name of the instructor
    name: str = ""
    full_name: str = ""
    # Email address of the instructor
    email: str
    # Role or title of the instructor
    role: str = "Instructor · Computer Science"
    # Arbitrary key-value dictionary containing custom UI and workflow preferences
    preferences: Dict[str, Any] = Field(default_factory=dict)


# Schema extending InstructorResponse for general user representations
class UserResponse(InstructorResponse):
    pass


# Schema for returning combined token and user profile upon login or signup
class AuthResponse(BaseModel):
    # The generated JWT access token string
    access_token: str
    # The token type identifier, defaulting to bearer
    token_type: str = "bearer"
    # Detailed user profile associated with the generated token
    user: UserResponse
