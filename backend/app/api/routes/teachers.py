from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import Department, Teacher, TeacherDepartment
from app.schemas.reference import TeacherCreate, TeacherRead, TeacherUpdate

router = APIRouter(prefix="/teachers", tags=["teachers"])
manage = require_permission(permissions.TEACHER_MANAGE)


def _to_read(teacher: Teacher) -> TeacherRead:
    return TeacherRead(
        id=teacher.id,
        first_name=teacher.first_name,
        last_name=teacher.last_name,
        middle_name=teacher.middle_name,
        full_name=teacher.full_name,
        degree=teacher.degree,
        position=teacher.position,
        is_active=teacher.is_active,
        department_ids=[link.department_id for link in teacher.department_links],
    )


def _get_or_404(db: Session, teacher_id: int) -> Teacher:
    teacher = db.get(Teacher, teacher_id)
    if teacher is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Викладача не знайдено")
    return teacher


@router.get("", response_model=list[TeacherRead])
def list_teachers(
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[TeacherRead]:
    teachers = db.scalars(select(Teacher).order_by(Teacher.last_name, Teacher.first_name)).all()
    if department_id is not None:
        teachers = [
            t for t in teachers if any(l.department_id == department_id for l in t.department_links)
        ]
    return [_to_read(t) for t in teachers]


@router.get("/{teacher_id}", response_model=TeacherRead)
def get_teacher(
    teacher_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> TeacherRead:
    return _to_read(_get_or_404(db, teacher_id))


@router.post("", response_model=TeacherRead, status_code=status.HTTP_201_CREATED)
def create_teacher(
    payload: TeacherCreate, db: Session = Depends(get_db), _=Depends(manage)
) -> TeacherRead:
    dept_ids = list(dict.fromkeys(payload.department_ids))
    existing = {d for d in db.scalars(select(Department.id).where(Department.id.in_(dept_ids)))}
    missing = set(dept_ids) - existing
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Кафедри не існують: {sorted(missing)}",
        )

    teacher = Teacher(
        first_name=payload.first_name,
        last_name=payload.last_name,
        middle_name=payload.middle_name,
        degree=payload.degree,
        position=payload.position,
    )
    teacher.department_links = [
        TeacherDepartment(
            department_id=d, is_primary=(d == payload.primary_department_id)
        )
        for d in dept_ids
    ]
    db.add(teacher)
    db.commit()
    db.refresh(teacher)
    return _to_read(teacher)


@router.patch("/{teacher_id}", response_model=TeacherRead)
def update_teacher(
    teacher_id: int,
    payload: TeacherUpdate,
    db: Session = Depends(get_db),
    _=Depends(manage),
) -> TeacherRead:
    teacher = _get_or_404(db, teacher_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(teacher, field, value)
    db.commit()
    db.refresh(teacher)
    return _to_read(teacher)


@router.delete("/{teacher_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_teacher(teacher_id: int, db: Session = Depends(get_db), _=Depends(manage)) -> None:
    db.delete(_get_or_404(db, teacher_id))
    db.commit()
