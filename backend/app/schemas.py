from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from .models import LabLanguage, SubmissionStatus


class StudentCreate(BaseModel):
    full_name: str
    telegram_username: Optional[str] = None


class StudentOut(StudentCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class LabCreate(BaseModel):
    title: str
    language: LabLanguage
    description: Optional[str] = None


class LabOut(LabCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionOut(BaseModel):
    id: int
    student_id: int
    lab_id: int
    filename: str
    status: SubmissionStatus
    checker_output: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SubmissionStatusUpdate(BaseModel):
    status: SubmissionStatus
