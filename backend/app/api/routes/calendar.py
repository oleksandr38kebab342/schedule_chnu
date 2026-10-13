from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import AcademicWeek, AcademicYear, CalendarException, Semester
from app.schemas.calendar import (
    AcademicWeekRead,
    AcademicYearCreate,
    AcademicYearRead,
    CalendarExceptionCreate,
    CalendarExceptionRead,
    SemesterCreate,
    SemesterRead,
    WeekForDateRead,
)
from app.services import calendar as calendar_service

router = APIRouter(tags=["calendar"])
manage = require_permission(permissions.CALENDAR_MANAGE)


# ---------- Academic years ----------
@router.get("/academic-years", response_model=list[AcademicYearRead])
def list_years(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[AcademicYear]:
    return list(db.scalars(select(AcademicYear).order_by(AcademicYear.starts_on)))


@router.post("/academic-years", response_model=AcademicYearRead, status_code=status.HTTP_201_CREATED)
def create_year(payload: AcademicYearCreate, db: Session = Depends(get_db), _=Depends(manage)) -> AcademicYear:
    if payload.ends_on <= payload.starts_on:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Дата завершення року має бути пізнішою за початок",
        )
    if db.scalar(select(AcademicYear).where(AcademicYear.name == payload.name)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Навчальний рік {payload.name} вже існує"
        )
    year = AcademicYear(**payload.model_dump())
    db.add(year)
    db.commit()
    db.refresh(year)
    return year


# ---------- Semesters ----------
@router.post("/semesters", response_model=SemesterRead, status_code=status.HTTP_201_CREATED)
def create_semester(payload: SemesterCreate, db: Session = Depends(get_db), _=Depends(manage)) -> Semester:
    if db.get(AcademicYear, payload.academic_year_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Навчальний рік {payload.academic_year_id} не існує",
        )
    if payload.end_date <= payload.start_date:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Дата завершення семестру має бути пізнішою за початок",
        )
    if db.scalar(
        select(Semester).where(
            Semester.academic_year_id == payload.academic_year_id,
            Semester.ordinal == payload.ordinal,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Семестр {payload.ordinal} цього року вже існує",
        )
    semester = Semester(**payload.model_dump())
    db.add(semester)
    db.commit()
    db.refresh(semester)
    return semester


@router.get("/semesters", response_model=list[SemesterRead])
def list_semesters(
    academic_year_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[Semester]:
    stmt = select(Semester).order_by(Semester.start_date)
    if academic_year_id is not None:
        stmt = stmt.where(Semester.academic_year_id == academic_year_id)
    return list(db.scalars(stmt))


def _get_semester(db: Session, semester_id: int) -> Semester:
    semester = db.get(Semester, semester_id)
    if semester is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Семестр не знайдено")
    return semester


@router.post(
    "/semesters/{semester_id}/generate-weeks",
    response_model=list[AcademicWeekRead],
    status_code=status.HTTP_201_CREATED,
)
def generate_weeks(semester_id: int, db: Session = Depends(get_db), _=Depends(manage)) -> list[AcademicWeek]:
    """Перегенеровує навчальні тижні семестру (ідемпотентно: старі замінюються)."""
    semester = _get_semester(db, semester_id)
    db.query(AcademicWeek).filter(AcademicWeek.semester_id == semester_id).delete()
    weeks = calendar_service.generate_weeks(semester)
    db.add_all(weeks)
    db.commit()
    return list(
        db.scalars(
            select(AcademicWeek)
            .where(AcademicWeek.semester_id == semester_id)
            .order_by(AcademicWeek.number)
        )
    )


@router.get("/semesters/{semester_id}/weeks", response_model=list[AcademicWeekRead])
def list_weeks(
    semester_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> list[AcademicWeek]:
    _get_semester(db, semester_id)
    return list(
        db.scalars(
            select(AcademicWeek)
            .where(AcademicWeek.semester_id == semester_id)
            .order_by(AcademicWeek.number)
        )
    )


@router.get("/semesters/{semester_id}/week-for-date", response_model=WeekForDateRead)
def week_for_date(
    semester_id: int,
    day: date = Query(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> WeekForDateRead:
    semester = _get_semester(db, semester_id)
    plan = calendar_service.week_for_date(semester, day)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Дата поза межами семестру"
        )
    return WeekForDateRead(
        number=plan.number, parity=plan.parity, starts_on=plan.starts_on, ends_on=plan.ends_on
    )


# ---------- Calendar exceptions ----------
@router.post(
    "/semesters/{semester_id}/exceptions",
    response_model=CalendarExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
def add_exception(
    semester_id: int,
    payload: CalendarExceptionCreate,
    db: Session = Depends(get_db),
    _=Depends(manage),
) -> CalendarException:
    _get_semester(db, semester_id)
    if payload.date_to < payload.date_from:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Кінцева дата винятку раніша за початкову",
        )
    exc = CalendarException(semester_id=semester_id, **payload.model_dump())
    db.add(exc)
    db.commit()
    db.refresh(exc)
    return exc


@router.get("/semesters/{semester_id}/exceptions", response_model=list[CalendarExceptionRead])
def list_exceptions(
    semester_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> list[CalendarException]:
    _get_semester(db, semester_id)
    return list(
        db.scalars(
            select(CalendarException)
            .where(CalendarException.semester_id == semester_id)
            .order_by(CalendarException.date_from)
        )
    )
