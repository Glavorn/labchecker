from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db

router = APIRouter(tags=["labs"])


@router.post("/api/labs", response_model=schemas.LabOut)
def create_lab(lab: schemas.LabCreate, db: Session = Depends(get_db)):
    obj = models.Lab(**lab.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/api/labs", response_model=List[schemas.LabOut])
def list_labs(db: Session = Depends(get_db)):
    return db.query(models.Lab).order_by(models.Lab.created_at.desc()).all()
