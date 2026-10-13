from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import Faculty
from app.schemas.organization import FacultyCreate, FacultyRead, FacultyUpdate

router = APIRouter(prefix="/faculties", tags=["faculties"])

manage = require_permission(permissions.FACULTY_MANAGE)


def _get_or_404(db: Session, faculty_id: int) -> Faculty:
    faculty = db.get(Faculty, faculty_id)
    if faculty is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Факультет не знайдено")
    return faculty


@router.get("", response_model=list[FacultyRead])
def list_faculties(
    db: Session = Depends(get_db), _=Depends(get_current_user)
) -> list[Faculty]:
    return list(db.scalars(select(Faculty).order_by(Faculty.name)))


@router.get("/{faculty_id}", response_model=FacultyRead)
def get_faculty(
    faculty_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> Faculty:
    return _get_or_404(db, faculty_id)


@router.post("", response_model=FacultyRead, status_code=status.HTTP_201_CREATED)
def create_faculty(
    payload: FacultyCreate, db: Session = Depends(get_db), _=Depends(manage)
) -> Faculty:
    if db.scalar(select(Faculty).where(Faculty.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Факультет з кодом {payload.code} вже існує",
        )

    faculty = Faculty(**payload.model_dump())
    db.add(faculty)
    db.commit()
    db.refresh(faculty)
    return faculty


@router.patch("/{faculty_id}", response_model=FacultyRead)
def update_faculty(
    faculty_id: int,
    payload: FacultyUpdate,
    db: Session = Depends(get_db),
    _=Depends(manage),
) -> Faculty:
    faculty = _get_or_404(db, faculty_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(faculty, field, value)
    db.commit()
    db.refresh(faculty)
    return faculty


@router.delete("/{faculty_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_faculty(
    faculty_id: int, db: Session = Depends(get_db), _=Depends(manage)
) -> None:
    db.delete(_get_or_404(db, faculty_id))
    db.commit()
