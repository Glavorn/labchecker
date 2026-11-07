from datetime import datetime, timezone
from typing import Annotated, Optional

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from .models import LabLanguage, SubmissionStatus


def _as_utc(value: datetime) -> datetime:
    # в бд naive utc, без tzinfo браузер считает время локальным
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


UtcDatetime = Annotated[datetime, AfterValidator(_as_utc)]


class StudentCreate(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    telegram_username: Optional[str] = Field(default=None, max_length=100)


class StudentOut(StudentCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: UtcDatetime


class StudentCreatedOut(StudentOut):
    invite_key: str


class InviteOut(BaseModel):
    invite_key: str


class LabCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    language: LabLanguage
    description: Optional[str] = None


class LabOut(LabCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: UtcDatetime


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    student_id: int
    student_name: str
    lab_id: int
    lab_title: str
    filename: str
    source_code: str
    status: SubmissionStatus
    checker_output: Optional[str]
    teacher_comment: Optional[str]
    reviewed_at: Optional[UtcDatetime]
    created_at: UtcDatetime


class SubmissionReview(BaseModel):
    status: SubmissionStatus
    teacher_comment: Optional[str] = Field(default=None, max_length=5000)
