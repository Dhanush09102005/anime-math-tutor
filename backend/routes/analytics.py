from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from db.database import get_db
from db import crud
from db.models import User
from auth.dependencies import get_current_user

router = APIRouter()


@router.get("/analytics")
def get_analytics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_analytics(db, current_user.id)


@router.get("/syllabus/progress")
def get_syllabus_progress(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return crud.get_syllabus_progress(db, current_user.id)
