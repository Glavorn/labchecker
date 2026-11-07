import os
from typing import List, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Security, UploadFile
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import checkers, models, schemas
from .auth import (
    current_student,
    is_teacher,
    new_invite_key,
    optional_student,
    require_teacher,
    teacher_token_header,
)
from .database import Base, engine, get_db

MAX_UPLOAD_BYTES = int(os.getenv("MAX_UPLOAD_BYTES", 256 * 1024))

# create_all не добавляет новые колонки в существующие таблицы
_MIGRATIONS = [
    "ALTER TABLE students ADD COLUMN IF NOT EXISTS invite_key_hash VARCHAR(64)",
    "CREATE UNIQUE INDEX IF NOT EXISTS ix_students_invite_key_hash ON students (invite_key_hash)",
    "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS teacher_comment TEXT",
    "ALTER TABLE submissions ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITHOUT TIME ZONE",
]

# lock чтобы реплики не создавали схему одновременно
with engine.begin() as conn:
    if conn.dialect.name == "postgresql":
        conn.execute(text("SELECT pg_advisory_xact_lock(727274)"))
    Base.metadata.create_all(bind=conn)
    if conn.dialect.name == "postgresql":
        for statement in _MIGRATIONS:
            conn.execute(text(statement))

app = FastAPI(
    title="LabChecker API",
    docs_url="/api/docs",
    redoc_url=None,
    openapi_url="/api/openapi.json",
)


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/auth/check", dependencies=[Depends(require_teacher)])
def auth_check():
    return {"teacher": True}


# me

@app.get("/api/me", response_model=schemas.StudentOut)
def me(student: models.Student = Depends(current_student)):
    return student


@app.get("/api/me/submissions", response_model=List[schemas.SubmissionOut])
def my_submissions(
    student: models.Student = Depends(current_student),
    db: Session = Depends(get_db),
):
    return (
        db.query(models.Submission)
        .filter(models.Submission.student_id == student.id)
        .order_by(models.Submission.created_at.desc(), models.Submission.id.desc())
        .all()
    )


# students

@app.post(
    "/api/students",
    response_model=schemas.StudentCreatedOut,
    dependencies=[Depends(require_teacher)],
)
def create_student(student: schemas.StudentCreate, db: Session = Depends(get_db)):
    key, key_hash = new_invite_key()
    obj = models.Student(**student.model_dump(), invite_key_hash=key_hash)
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return {**schemas.StudentOut.model_validate(obj).model_dump(), "invite_key": key}


@app.post(
    "/api/students/{student_id}/invite",
    response_model=schemas.InviteOut,
    dependencies=[Depends(require_teacher)],
)
def regenerate_invite(student_id: int, db: Session = Depends(get_db)):
    student = db.get(models.Student, student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Студент не найден")
    key, student.invite_key_hash = new_invite_key()
    db.commit()
    return {"invite_key": key}


@app.get(
    "/api/students",
    response_model=List[schemas.StudentOut],
    dependencies=[Depends(require_teacher)],
)
def list_students(db: Session = Depends(get_db)):
    return db.query(models.Student).order_by(models.Student.full_name).all()


# labs

@app.post(
    "/api/labs",
    response_model=schemas.LabOut,
    dependencies=[Depends(require_teacher)],
)
def create_lab(lab: schemas.LabCreate, db: Session = Depends(get_db)):
    obj = models.Lab(**lab.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@app.get("/api/labs", response_model=List[schemas.LabOut])
def list_labs(db: Session = Depends(get_db)):
    return db.query(models.Lab).order_by(models.Lab.created_at.desc()).all()


# submissions

# не async: линтер может работать до 15 сек, пусть крутится в threadpool
@app.post("/api/submissions", response_model=schemas.SubmissionOut)
def create_submission(
    lab_id: int = Form(...),
    file: UploadFile = File(...),
    student_id: Optional[int] = Form(None),
    student: Optional[models.Student] = Depends(optional_student),
    teacher_token: Optional[str] = Security(teacher_token_header),
    db: Session = Depends(get_db),
):
    if student is not None:
        owner_id = student.id
    elif is_teacher(teacher_token):
        if student_id is None:
            raise HTTPException(status_code=422, detail="Укажите student_id")
        if db.get(models.Student, student_id) is None:
            raise HTTPException(status_code=404, detail="Студент не найден")
        owner_id = student_id
    else:
        raise HTTPException(status_code=401, detail="Откройте свою личную ссылку")

    lab = db.get(models.Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Лаба не найдена")

    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Файл больше {MAX_UPLOAD_BYTES // 1024} КБ",
        )
    raw = data.decode("utf-8", errors="replace")

    filename = os.path.basename((file.filename or "").replace("\\", "/"))[:255] or "solution"
    output, has_issues = checkers.run_check(lab.language, raw, filename)

    submission = models.Submission(
        student_id=owner_id,
        lab_id=lab_id,
        filename=filename,
        source_code=raw,
        checker_output=output,
        status=(
            models.SubmissionStatus.needs_revision
            if has_issues
            else models.SubmissionStatus.checked
        ),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)
    return submission


@app.get(
    "/api/submissions",
    response_model=List[schemas.SubmissionOut],
    dependencies=[Depends(require_teacher)],
)
def list_submissions(
    student_id: Optional[int] = None,
    lab_id: Optional[int] = None,
    status: Optional[models.SubmissionStatus] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Submission)
    if student_id is not None:
        query = query.filter(models.Submission.student_id == student_id)
    if lab_id is not None:
        query = query.filter(models.Submission.lab_id == lab_id)
    if status is not None:
        query = query.filter(models.Submission.status == status)
    return query.order_by(models.Submission.created_at.desc(), models.Submission.id.desc()).all()


@app.patch(
    "/api/submissions/{submission_id}",
    response_model=schemas.SubmissionOut,
    dependencies=[Depends(require_teacher)],
)
def review_submission(
    submission_id: int,
    payload: schemas.SubmissionReview,
    db: Session = Depends(get_db),
):
    submission = db.get(models.Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Сдача не найдена")
    submission.status = payload.status
    if payload.teacher_comment is not None:
        submission.teacher_comment = payload.teacher_comment.strip() or None
    submission.reviewed_at = models.utcnow()
    db.commit()
    db.refresh(submission)
    return submission
