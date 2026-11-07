import hashlib
import os
import secrets

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from sqlalchemy.orm import Session

from . import models
from .database import get_db

teacher_token_header = APIKeyHeader(name="X-Teacher-Token", auto_error=False)
student_key_header = APIKeyHeader(name="X-Student-Key", auto_error=False)


def is_teacher(token: str | None) -> bool:
    expected = os.getenv("TEACHER_TOKEN", "")
    return bool(expected and token and secrets.compare_digest(token, expected))


def require_teacher(token: str | None = Security(teacher_token_header)) -> None:
    if not os.getenv("TEACHER_TOKEN", ""):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TEACHER_TOKEN не настроен на сервере",
        )
    if not is_teacher(token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Нужен токен преподавателя",
        )


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def new_invite_key() -> tuple[str, str]:
    key = secrets.token_urlsafe(32)
    return key, hash_key(key)


def optional_student(
    key: str | None = Security(student_key_header),
    db: Session = Depends(get_db),
) -> models.Student | None:
    if not key:
        return None
    return (
        db.query(models.Student)
        .filter(models.Student.invite_key_hash == hash_key(key))
        .one_or_none()
    )


def current_student(
    student: models.Student | None = Depends(optional_student),
) -> models.Student:
    if student is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Ссылка недействительна — попросите у преподавателя новую",
        )
    return student
