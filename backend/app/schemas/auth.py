"""Authentication and User schemas."""

from typing import Optional, Dict, Any
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    sub: Optional[str] = None
    exp: Optional[int] = None


class UserSignUp(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: Optional[str] = "Instructor · Computer Science"


class InstructorLogin(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class TeacherPreferencesUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    default_course: Optional[str] = None
    show_similarity_context: Optional[bool] = None
    require_teacher_notes_on_overrides: Optional[bool] = None
    include_ai_content_indicator: Optional[bool] = None


class InstructorResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    email: str
    role: str
    preferences: Dict[str, Any] = Field(default_factory=dict)


class UserResponse(InstructorResponse):
    pass


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
