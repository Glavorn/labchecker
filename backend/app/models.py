import enum
from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class LabLanguage(str, enum.Enum):
    python = "python"
    bash = "bash"


class SubmissionStatus(str, enum.Enum):
    pending = "pending"
    checked = "checked"
    needs_revision = "needs_revision"
    accepted = "accepted"


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True)
    full_name = Column(String(255), nullable=False)
    telegram_username = Column(String(100), nullable=True)
    # храним только sha256 от ключа
    invite_key_hash = Column(String(64), nullable=True, unique=True, index=True)
    created_at = Column(DateTime, default=utcnow)

    submissions = relationship("Submission", back_populates="student")


class Lab(Base):
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    language = Column(Enum(LabLanguage), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    submissions = relationship("Submission", back_populates="lab")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    source_code = Column(Text, nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.pending)
    checker_output = Column(Text, nullable=True)
    teacher_comment = Column(Text, nullable=True)
    reviewed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utcnow)

    student = relationship("Student", back_populates="submissions")
    lab = relationship("Lab", back_populates="submissions")

    @property
    def student_name(self) -> str:
        return self.student.full_name

    @property
    def lab_title(self) -> str:
        return self.lab.title
