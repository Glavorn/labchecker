import enum
from datetime import datetime

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum, LargeBinary
from sqlalchemy.orm import relationship

from .database import Base


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
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("Submission", back_populates="student")


class Lab(Base):
    __tablename__ = "labs"

    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    language = Column(Enum(LabLanguage), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    submissions = relationship("Submission", back_populates="lab")


class Submission(Base):
    __tablename__ = "submissions"

    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey("students.id"), nullable=False)
    lab_id = Column(Integer, ForeignKey("labs.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    file_data = Column(LargeBinary, nullable=False)
    status = Column(Enum(SubmissionStatus), default=SubmissionStatus.pending)
    checker_output = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    student = relationship("Student", back_populates="submissions")
    lab = relationship("Lab", back_populates="submissions")
