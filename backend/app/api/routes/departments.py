from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import Department, Faculty
from app.schemas.organization import DepartmentCreate, DepartmentRead, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["departments"])

manage = require_permission(permissions.DEPARTMENT_MANAGE)


def _get_or_404(db: Session, department_id: int) -> Department:
    department = db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Кафедру не знайдено")
    return department


@router.get("", response_model=list[DepartmentRead])
def list_departments(
    faculty_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[Department]:
    stmt = select(Department).order_by(Department.name)
    if faculty_id is not None:
        stmt = stmt.where(Department.faculty_id == faculty_id)
    return list(db.scalars(stmt))


@router.get("/{department_id}", response_model=DepartmentRead)
def get_department(
    department_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> Department:
    return _get_or_404(db, department_id)


@router.post("", response_model=DepartmentRead, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate, db: Session = Depends(get_db), _=Depends(manage)
) -> Department:
    if db.get(Faculty, payload.faculty_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Факультет {payload.faculty_id} не існує",
        )
    if db.scalar(select(Department).where(Department.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Кафедра з кодом {payload.code} вже існує",
        )

    department = Department(**payload.model_dump())
    db.add(department)
    db.commit()
    db.refresh(department)
    return department


@router.patch("/{department_id}", response_model=DepartmentRead)
def update_department(
    department_id: int,
    payload: DepartmentUpdate,
    db: Session = Depends(get_db),
    _=Depends(manage),
) -> Department:
    department = _get_or_404(db, department_id)
    data = payload.model_dump(exclude_unset=True)

    if data.get("parent_id") == department_id:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Кафедра не може бути власним батьківським підрозділом",
        )

    for field, value in data.items():
        setattr(department, field, value)
    db.commit()
    db.refresh(department)
    return department


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int, db: Session = Depends(get_db), _=Depends(manage)
) -> None:
    db.delete(_get_or_404(db, department_id))
    db.commit()
