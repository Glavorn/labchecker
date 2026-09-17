from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..services import checker

router = APIRouter(tags=["submissions"])


@router.post("/api/submissions", response_model=schemas.SubmissionOut)
async def create_submission(
    student_id: int = Form(...),
    lab_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    lab = db.get(models.Lab, lab_id)
    if lab is None:
        raise HTTPException(status_code=404, detail="Лаба не найдена")
    if db.get(models.Student, student_id) is None:
        raise HTTPException(status_code=404, detail="Студент не найден")

    file_bytes = await file.read()
    output, has_issues = checker.run_check(lab.language, file.filename, file_bytes)

    submission = models.Submission(
        student_id=student_id,
        lab_id=lab_id,
        filename=file.filename,
        file_data=file_bytes,
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


@router.get("/api/submissions", response_model=List[schemas.SubmissionOut])
def list_submissions(
    student_id: Optional[int] = None,
    lab_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    query = db.query(models.Submission)
    if student_id is not None:
        query = query.filter(models.Submission.student_id == student_id)
    if lab_id is not None:
        query = query.filter(models.Submission.lab_id == lab_id)
    return query.order_by(models.Submission.created_at.desc()).all()


@router.patch("/api/submissions/{submission_id}", response_model=schemas.SubmissionOut)
def update_submission_status(
    submission_id: int,
    payload: schemas.SubmissionStatusUpdate,
    db: Session = Depends(get_db),
):
    submission = db.get(models.Submission, submission_id)
    if submission is None:
        raise HTTPException(status_code=404, detail="Сдача не найдена")
    submission.status = payload.status
    db.commit()
    db.refresh(submission)
    return submission
