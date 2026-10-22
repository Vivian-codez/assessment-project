"""Classroom and Student roll-call schemas for Supabase educator workflow."""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class StudentItem(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    roll_number: str
    full_name: str
    email: Optional[str] = None


class StudentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    classroom_id: str
    roll_number: str
    full_name: str
    email: Optional[str] = None
    created_at: Optional[str] = None


class StudentUploadCSVResponse(BaseModel):
    total_inserted: int
    total_skipped: int
    skipped: List[Dict[str, Any]] = []
    inserted: List[Dict[str, Any]] = []


class ClassroomCreate(BaseModel):
    name: str
    code: str


class ClassroomResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    code: str
    instructor_id: Optional[str] = None
    students_count: int = 0
    created_at: Optional[str] = None
