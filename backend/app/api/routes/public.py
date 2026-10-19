"""Публічний перегляд розкладу — те, що відкривають студент і викладач.

Ці ендпоінти лише читають опублікований розклад і не потребують входу
(поки `PUBLIC_SCHEDULE_ENABLED` увімкнено). Усе, що змінює дані, лишається в
захищених роутерах із перевіркою прав на backend.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import (
    Building,
    Department,
    Faculty,
    Group,
    LessonType,
    PairTime,
    Room,
    Semester,
    Subgroup,
    Teacher,
    natural_key,
    normalize_room_code,
)
from app.schemas.view import (
    CalendarInfo,
    DayView,
    GroupOption,
    LessonTypeOption,
    PairTimeOption,
    RoomOption,
    SubgroupOption,
    TeacherOption,
    WeekView,
)
from app.services import calendar as calendar_service
from app.services import schedule_view
from app.services.schedule_view import Target, TargetKind

router = APIRouter(prefix="/public", tags=["public"])


def public_access() -> None:
    """Вимикач публічного доступу: з ним розклад закривається за входом."""
    if not settings.public_schedule_enabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Публічний перегляд розкладу вимкнено адміністратором",
        )


public = Depends(public_access)


# ---------- довідники для фільтрів ----------


@router.get("/groups", response_model=list[GroupOption])
def list_groups(
    search: str | None = Query(default=None),
    faculty_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> list[GroupOption]:
    departments = {d.id: d for d in db.scalars(select(Department))}
    faculties = {f.id: f for f in db.scalars(select(Faculty))}

    options: list[GroupOption] = []
    for group in db.scalars(select(Group).where(Group.is_active.is_(True))):
        department = departments.get(group.department_id)
        faculty = faculties.get(department.faculty_id) if department else None
        if faculty_id is not None and (faculty is None or faculty.id != faculty_id):
            continue
        if search and search.strip().lower() not in group.name.lower():
            continue
        options.append(
            GroupOption(
                id=group.id,
                name=group.name,
                course=group.course,
                department_id=department.id if department else None,
                department_name=department.name if department else None,
                faculty_id=faculty.id if faculty else None,
                faculty_name=faculty.name if faculty else None,
                faculty_short_name=faculty.short_name if faculty else None,
            )
        )
    # КН-1, КН-2, КН-10 — природний порядок, а не лексикографічний.
    return sorted(options, key=lambda o: natural_key(o.name))


@router.get("/groups/{group_id}/subgroups", response_model=list[SubgroupOption])
def list_subgroups(group_id: int, db: Session = Depends(get_db), _=public) -> list[Subgroup]:
    if db.get(Group, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Групу не знайдено")
    subgroups = list(db.scalars(select(Subgroup).where(Subgroup.group_id == group_id)))
    return sorted(subgroups, key=lambda s: natural_key(s.name))


@router.get("/teachers", response_model=list[TeacherOption])
def list_teachers(
    search: str | None = Query(default=None), db: Session = Depends(get_db), _=public
) -> list[TeacherOption]:
    needle = (search or "").strip().lower()
    options: list[TeacherOption] = []
    for teacher in db.scalars(
        select(Teacher)
        .where(Teacher.is_active.is_(True))
        .order_by(Teacher.last_name, Teacher.first_name)
    ):
        if needle and needle not in teacher.full_name.lower():
            continue
        options.append(
            TeacherOption(
                id=teacher.id,
                full_name=teacher.full_name,
                short_name=teacher.short_name or teacher.full_name,
                degree=teacher.degree,
                position=teacher.position,
                department_names=[
                    link.department.name for link in teacher.department_links if link.department
                ],
            )
        )
    return options


@router.get("/rooms", response_model=list[RoomOption])
def list_rooms(
    search: str | None = Query(default=None), db: Session = Depends(get_db), _=public
) -> list[RoomOption]:
    buildings = {b.id: b for b in db.scalars(select(Building))}
    needle = normalize_room_code(search) if search else None

    options: list[RoomOption] = []
    for room in db.scalars(select(Room).where(Room.is_active.is_(True))):
        if needle:
            keys = {room.normalized} | {a.normalized for a in room.aliases}
            if not any(needle in key for key in keys):
                continue
        building = buildings.get(room.building_id)
        options.append(
            RoomOption(
                id=room.id,
                number=room.number,
                building_id=room.building_id,
                building_code=building.code if building else "",
                building_name=building.name if building else "",
                floor=room.floor,
                capacity=room.capacity,
            )
        )
    return sorted(options, key=lambda o: (o.building_code, natural_key(o.number)))


@router.get("/lesson-types", response_model=list[LessonTypeOption])
def list_lesson_types(db: Session = Depends(get_db), _=public) -> list[LessonType]:
    return list(db.scalars(select(LessonType).order_by(LessonType.code)))


@router.get("/times", response_model=list[PairTimeOption])
def list_times(db: Session = Depends(get_db), _=public) -> list[PairTime]:
    return list(db.scalars(select(PairTime).order_by(PairTime.number)))


# ---------- календар ----------


@router.get("/calendar", response_model=CalendarInfo)
def calendar_info(
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> CalendarInfo:
    """Семестр, номер навчального тижня і парність для дати (типово — сьогодні)."""
    target_day = day or date.today()
    semester = (
        db.get(Semester, semester_id)
        if semester_id is not None
        else schedule_view.current_semester(db, target_day)
    )
    if semester is None:
        return CalendarInfo(
            day=target_day,
            semester_id=None,
            semester_name=None,
            semester_start=None,
            semester_end=None,
            week_number=None,
            parity=None,
            week_starts_on=None,
            week_ends_on=None,
            is_working=False,
            closed_reason="Навчальний семестр не налаштовано",
        )

    week = calendar_service.week_for_date(semester, target_day)
    is_working, closed_reason = schedule_view.day_state(db, semester, target_day)
    return CalendarInfo(
        day=target_day,
        semester_id=semester.id,
        semester_name=semester.name,
        semester_start=semester.start_date,
        semester_end=semester.end_date,
        week_number=week.number if week else None,
        parity=week.parity if week else None,
        week_starts_on=week.starts_on if week else None,
        week_ends_on=week.ends_on if week else None,
        is_working=is_working and week is not None,
        closed_reason=closed_reason
        or (None if week else "Дата поза межами семестру"),
    )


# ---------- розклад ----------


def _target_or_404(db: Session, kind: TargetKind, target_id: int) -> Target:
    model, message = {
        TargetKind.GROUP: (Group, "Групу не знайдено"),
        TargetKind.TEACHER: (Teacher, "Викладача не знайдено"),
        TargetKind.ROOM: (Room, "Аудиторію не знайдено"),
    }[kind]
    if db.get(model, target_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=message)
    return Target(kind=kind, id=target_id)


def _day(
    db: Session,
    kind: TargetKind,
    target_id: int,
    day: date | None,
    semester_id: int | None,
    subgroup_id: int | None = None,
) -> DayView:
    target = _target_or_404(db, kind, target_id)
    return DayView.model_validate(
        schedule_view.day_view(
            db,
            target=target,
            day=day or date.today(),
            semester_id=semester_id,
            subgroup_id=subgroup_id,
        )
    )


def _week(
    db: Session,
    kind: TargetKind,
    target_id: int,
    day: date | None,
    semester_id: int | None,
    subgroup_id: int | None = None,
) -> WeekView:
    target = _target_or_404(db, kind, target_id)
    return WeekView.model_validate(
        schedule_view.week_view(
            db,
            target=target,
            day=day or date.today(),
            semester_id=semester_id,
            subgroup_id=subgroup_id,
        )
    )


@router.get("/schedule/group/{group_id}/day", response_model=DayView)
def group_day(
    group_id: int,
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    subgroup_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> DayView:
    return _day(db, TargetKind.GROUP, group_id, day, semester_id, subgroup_id)


@router.get("/schedule/group/{group_id}/week", response_model=WeekView)
def group_week(
    group_id: int,
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    subgroup_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> WeekView:
    return _week(db, TargetKind.GROUP, group_id, day, semester_id, subgroup_id)


@router.get("/schedule/teacher/{teacher_id}/day", response_model=DayView)
def teacher_day(
    teacher_id: int,
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> DayView:
    return _day(db, TargetKind.TEACHER, teacher_id, day, semester_id)


@router.get("/schedule/teacher/{teacher_id}/week", response_model=WeekView)
def teacher_week(
    teacher_id: int,
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> WeekView:
    return _week(db, TargetKind.TEACHER, teacher_id, day, semester_id)


@router.get("/schedule/room/{room_id}/day", response_model=DayView)
def room_day(
    room_id: int,
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> DayView:
    return _day(db, TargetKind.ROOM, room_id, day, semester_id)


@router.get("/schedule/room/{room_id}/week", response_model=WeekView)
def room_week(
    room_id: int,
    day: date | None = Query(default=None, alias="date"),
    semester_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=public,
) -> WeekView:
    return _week(db, TargetKind.ROOM, room_id, day, semester_id)
