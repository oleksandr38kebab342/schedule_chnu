"""Денормалізоване представлення розкладу на конкретну дату (ТЗ, розділи 29-33).

Базове заняття зберігається шаблоном «день тижня + пара + парність». Щоб
показати його студентові чи викладачеві, шаблон треба розгорнути на дату:

1. знайти семестр, що містить дату, і навчальний тиждень у ньому;
2. відібрати заняття цього дня, парність яких збігається з парністю тижня;
3. прибрати дні, закриті календарними винятками (свята, канікули);
4. накласти точкові зміни заняття (скасування, перенесення, заміна);
5. підставити назви дисциплін, викладачів і аудиторій замість ідентифікаторів.

Сервіс не залежить від HTTP: приймає сесію БД і повертає dataclass-и.
"""

import enum
from dataclasses import dataclass, field
from datetime import date, time, timedelta

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.models import (
    Building,
    CalendarException,
    ExceptionAction,
    ExceptionKind,
    Group,
    LessonType,
    PairTime,
    Parity,
    Room,
    ScheduleEntry,
    ScheduleException,
    ScheduleGroup,
    ScheduleRoom,
    ScheduleStream,
    ScheduleSubgroup,
    ScheduleTeacher,
    Semester,
    Stream,
    StreamGroup,
    Subgroup,
    Subject,
    Teacher,
)
from app.services import calendar as calendar_service


class TargetKind(str, enum.Enum):
    GROUP = "group"
    TEACHER = "teacher"
    ROOM = "room"


class LessonStatus(str, enum.Enum):
    NORMAL = "NORMAL"
    ADDED = "ADDED"          # додаткове заняття саме на цю дату
    MOVED_IN = "MOVED_IN"    # перенесене на цю дату з іншої
    MOVED_OUT = "MOVED_OUT"  # перенесене з цієї дати на іншу
    SHIFTED = "SHIFTED"      # перенесене в межах дня (інша пара / аудиторія)
    REPLACED = "REPLACED"    # заміна викладача або аудиторії
    CANCELLED = "CANCELLED"


@dataclass(frozen=True)
class Target:
    kind: TargetKind
    id: int


@dataclass(frozen=True)
class RoomView:
    id: int
    number: str
    building_code: str
    building_name: str
    floor: int | None = None


@dataclass(frozen=True)
class TeacherView:
    id: int
    full_name: str
    short_name: str
    degree: str | None = None
    position: str | None = None
    is_substitute: bool = False


@dataclass(frozen=True)
class LessonView:
    entry_id: int
    pair_number: int
    pair_label: str | None
    starts_at: time
    ends_at: time
    day_of_week: int
    week_parity: Parity
    subject_name: str
    subject_short: str | None
    lesson_type_code: str
    lesson_type_name: str
    lesson_type_short: str | None
    teachers: list[TeacherView] = field(default_factory=list)
    rooms: list[RoomView] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    subgroups: list[str] = field(default_factory=list)
    streams: list[str] = field(default_factory=list)
    note: str | None = None
    status: LessonStatus = LessonStatus.NORMAL
    change_reason: str | None = None
    moved_to: date | None = None
    moved_from: date | None = None


@dataclass(frozen=True)
class DayView:
    day: date
    day_of_week: int
    semester_id: int | None
    semester_name: str | None
    week_number: int | None
    parity: Parity | None
    is_working: bool
    closed_reason: str | None
    lessons: list[LessonView] = field(default_factory=list)


@dataclass(frozen=True)
class WeekView:
    starts_on: date
    ends_on: date
    semester_id: int | None
    semester_name: str | None
    week_number: int | None
    parity: Parity | None
    days: list[DayView] = field(default_factory=list)


_CLOSED_KINDS = {ExceptionKind.HOLIDAY, ExceptionKind.VACATION}

_KIND_LABEL = {
    ExceptionKind.HOLIDAY: "Святковий день",
    ExceptionKind.VACATION: "Канікули",
    ExceptionKind.WORKING_DAY: "Робочий день",
    ExceptionKind.REMOTE: "Дистанційний день",
}


def monday_of(day: date) -> date:
    return day - timedelta(days=day.weekday())


def resolve_semester(db: Session, day: date, semester_id: int | None = None) -> Semester | None:
    """Семестр для дати. Явний semester_id має пріоритет над пошуком за датою."""
    if semester_id is not None:
        return db.get(Semester, semester_id)
    return db.scalar(
        select(Semester)
        .where(Semester.start_date <= day, Semester.end_date >= day)
        .order_by(Semester.start_date)
    )


def current_semester(db: Session, today: date) -> Semester | None:
    """Семестр, що триває зараз, інакше найближчий майбутній, інакше останній."""
    running = resolve_semester(db, today)
    if running is not None:
        return running
    upcoming = db.scalar(
        select(Semester).where(Semester.start_date > today).order_by(Semester.start_date)
    )
    if upcoming is not None:
        return upcoming
    return db.scalar(select(Semester).order_by(Semester.start_date.desc()))


# ---------- внутрішні довідники ----------


class _Lookups:
    """Довідники, прочитані один раз на запит (назви дисциплін, аудиторій тощо)."""

    def __init__(self, db: Session) -> None:
        self.subjects = {s.id: s for s in db.scalars(select(Subject))}
        self.lesson_types = {t.id: t for t in db.scalars(select(LessonType))}
        self.teachers = {t.id: t for t in db.scalars(select(Teacher))}
        self.pairs = {p.id: p for p in db.scalars(select(PairTime))}
        self.groups = {g.id: g for g in db.scalars(select(Group))}
        self.subgroups = {s.id: s for s in db.scalars(select(Subgroup))}
        self.streams = {s.id: s for s in db.scalars(select(Stream))}
        buildings = {b.id: b for b in db.scalars(select(Building))}
        self.rooms = {
            r.id: RoomView(
                id=r.id,
                number=r.number,
                building_code=buildings[r.building_id].code if r.building_id in buildings else "",
                building_name=buildings[r.building_id].name if r.building_id in buildings else "",
                floor=r.floor,
            )
            for r in db.scalars(select(Room))
        }

    def teacher_view(self, teacher_id: int, *, is_substitute: bool = False) -> TeacherView | None:
        teacher = self.teachers.get(teacher_id)
        if teacher is None:
            return None
        return TeacherView(
            id=teacher.id,
            full_name=teacher.full_name,
            short_name=teacher.short_name or teacher.full_name,
            degree=teacher.degree,
            position=teacher.position,
            is_substitute=is_substitute,
        )


def _target_entry_ids(db: Session, target: Target, semester_id: int) -> set[int]:
    """Ідентифікатори занять, що стосуються групи / викладача / аудиторії.

    Для групи враховуються три способи прив'язки: пряма, через підгрупу цієї
    групи і через потік, що містить групу.
    """
    if target.kind is TargetKind.GROUP:
        subgroup_ids = select(Subgroup.id).where(Subgroup.group_id == target.id)
        stream_ids = select(StreamGroup.stream_id).where(StreamGroup.group_id == target.id)
        stmt = (
            select(ScheduleEntry.id)
            .outerjoin(ScheduleGroup, ScheduleGroup.entry_id == ScheduleEntry.id)
            .outerjoin(ScheduleSubgroup, ScheduleSubgroup.entry_id == ScheduleEntry.id)
            .outerjoin(ScheduleStream, ScheduleStream.entry_id == ScheduleEntry.id)
            .where(
                ScheduleEntry.semester_id == semester_id,
                or_(
                    ScheduleGroup.group_id == target.id,
                    ScheduleSubgroup.subgroup_id.in_(subgroup_ids),
                    ScheduleStream.stream_id.in_(stream_ids),
                ),
            )
        )
    elif target.kind is TargetKind.TEACHER:
        # Викладач бачить і ті пари, на які його призначили заміною.
        substituted = select(ScheduleException.entry_id).where(
            ScheduleException.new_teacher_id == target.id
        )
        stmt = (
            select(ScheduleEntry.id)
            .outerjoin(ScheduleTeacher, ScheduleTeacher.entry_id == ScheduleEntry.id)
            .where(
                ScheduleEntry.semester_id == semester_id,
                or_(ScheduleTeacher.teacher_id == target.id, ScheduleEntry.id.in_(substituted)),
            )
        )
    else:
        moved_here = select(ScheduleException.entry_id).where(
            ScheduleException.new_room_id == target.id
        )
        stmt = (
            select(ScheduleEntry.id)
            .outerjoin(ScheduleRoom, ScheduleRoom.entry_id == ScheduleEntry.id)
            .where(
                ScheduleEntry.semester_id == semester_id,
                or_(ScheduleRoom.room_id == target.id, ScheduleEntry.id.in_(moved_here)),
            )
        )
    return set(db.scalars(stmt))


def _matches_subgroup(entry: ScheduleEntry, subgroup_id: int | None) -> bool:
    """Фільтр підгрупи: загальні пари бачать усі, пари іншої підгрупи — ні."""
    if subgroup_id is None or not entry.subgroups:
        return True
    return any(link.subgroup_id == subgroup_id for link in entry.subgroups)


def _closed_reason(exceptions: list[CalendarException], day: date) -> str | None:
    for exc in exceptions:
        if exc.date_from <= day <= exc.date_to and exc.kind in _CLOSED_KINDS:
            return exc.description or _KIND_LABEL[exc.kind]
    return None


def _day_note(exceptions: list[CalendarException], day: date) -> str | None:
    for exc in exceptions:
        if exc.date_from <= day <= exc.date_to and exc.kind is ExceptionKind.REMOTE:
            return exc.description or _KIND_LABEL[ExceptionKind.REMOTE]
    return None


def _build_lesson(
    entry: ScheduleEntry,
    lookups: _Lookups,
    *,
    status: LessonStatus,
    pair_time_id: int,
    extra_room_id: int | None = None,
    substitute_teacher_id: int | None = None,
    change_reason: str | None = None,
    moved_to: date | None = None,
    moved_from: date | None = None,
    day_note: str | None = None,
) -> LessonView | None:
    pair = lookups.pairs.get(pair_time_id)
    subject = lookups.subjects.get(entry.subject_id)
    lesson_type = lookups.lesson_types.get(entry.lesson_type_id)
    if pair is None or subject is None or lesson_type is None:
        return None  # зламане посилання на довідник не має рушити весь день

    if substitute_teacher_id is not None:
        substitute = lookups.teacher_view(substitute_teacher_id, is_substitute=True)
        teachers = [substitute] if substitute else []
    else:
        teachers = [
            t
            for t in (lookups.teacher_view(link.teacher_id) for link in entry.teachers)
            if t is not None
        ]

    if extra_room_id is not None:
        rooms = [lookups.rooms[extra_room_id]] if extra_room_id in lookups.rooms else []
    else:
        rooms = [lookups.rooms[link.room_id] for link in entry.rooms if link.room_id in lookups.rooms]

    subgroup_names = []
    for link in entry.subgroups:
        subgroup = lookups.subgroups.get(link.subgroup_id)
        if subgroup is not None:
            subgroup_names.append(subgroup.name)

    stream_names = []
    for link in entry.streams:
        stream = lookups.streams.get(link.stream_id)
        if stream is not None:
            stream_names.append(stream.name)

    note = entry.note
    if day_note:
        note = f"{note} · {day_note}" if note else day_note

    return LessonView(
        entry_id=entry.id,
        pair_number=pair.number,
        pair_label=pair.label,
        starts_at=pair.starts_at,
        ends_at=pair.ends_at,
        day_of_week=entry.day_of_week,
        week_parity=entry.week_parity,
        subject_name=subject.name,
        subject_short=subject.short_name,
        lesson_type_code=lesson_type.code,
        lesson_type_name=lesson_type.name,
        lesson_type_short=lesson_type.short_name,
        teachers=teachers,
        rooms=rooms,
        groups=[
            lookups.groups[link.group_id].name
            for link in entry.groups
            if link.group_id in lookups.groups
        ],
        subgroups=subgroup_names,
        streams=stream_names,
        note=note,
        status=status,
        change_reason=change_reason,
        moved_to=moved_to,
        moved_from=moved_from,
    )


def _resolve_occurrence(
    entry: ScheduleEntry,
    day: date,
    parity: Parity,
    exceptions: list[ScheduleException],
    lookups: _Lookups,
    day_note: str | None,
) -> LessonView | None:
    """Чи відбувається заняття цього дня і в якому вигляді."""
    on_date = [e for e in exceptions if e.on_date == day]
    moved_in = [
        e
        for e in exceptions
        if e.action is ExceptionAction.MOVE and e.new_date == day and e.on_date != day
    ]
    added = [e for e in on_date if e.action is ExceptionAction.ADD]

    pattern_match = entry.day_of_week == day.isoweekday() and (
        entry.week_parity is Parity.BOTH or entry.week_parity is parity
    )

    if pattern_match:
        cancelled = next((e for e in on_date if e.action is ExceptionAction.CANCEL), None)
        if cancelled is not None:
            return _build_lesson(
                entry,
                lookups,
                status=LessonStatus.CANCELLED,
                pair_time_id=entry.pair_time_id,
                change_reason=cancelled.reason,
                day_note=day_note,
            )

        moved = next((e for e in on_date if e.action is ExceptionAction.MOVE), None)
        if moved is not None:
            if moved.new_date is not None and moved.new_date != day:
                return _build_lesson(
                    entry,
                    lookups,
                    status=LessonStatus.MOVED_OUT,
                    pair_time_id=entry.pair_time_id,
                    change_reason=moved.reason,
                    moved_to=moved.new_date,
                    day_note=day_note,
                )
            return _build_lesson(
                entry,
                lookups,
                status=LessonStatus.SHIFTED,
                pair_time_id=moved.new_pair_time_id or entry.pair_time_id,
                extra_room_id=moved.new_room_id,
                change_reason=moved.reason,
                day_note=day_note,
            )

        replaced = next((e for e in on_date if e.action is ExceptionAction.REPLACE), None)
        if replaced is not None:
            return _build_lesson(
                entry,
                lookups,
                status=LessonStatus.REPLACED,
                pair_time_id=replaced.new_pair_time_id or entry.pair_time_id,
                extra_room_id=replaced.new_room_id,
                substitute_teacher_id=replaced.new_teacher_id,
                change_reason=replaced.reason,
                day_note=day_note,
            )

        return _build_lesson(
            entry,
            lookups,
            status=LessonStatus.NORMAL,
            pair_time_id=entry.pair_time_id,
            day_note=day_note,
        )

    if moved_in:
        exc = moved_in[0]
        return _build_lesson(
            entry,
            lookups,
            status=LessonStatus.MOVED_IN,
            pair_time_id=exc.new_pair_time_id or entry.pair_time_id,
            extra_room_id=exc.new_room_id,
            change_reason=exc.reason,
            moved_from=exc.on_date,
            day_note=day_note,
        )

    if added:
        exc = added[0]
        return _build_lesson(
            entry,
            lookups,
            status=LessonStatus.ADDED,
            pair_time_id=exc.new_pair_time_id or entry.pair_time_id,
            extra_room_id=exc.new_room_id,
            substitute_teacher_id=exc.new_teacher_id,
            change_reason=exc.reason,
            day_note=day_note,
        )

    return None


def _load_context(
    db: Session, target: Target, semester: Semester
) -> tuple[_Lookups, dict[int, ScheduleEntry], dict[int, list[ScheduleException]]]:
    entry_ids = _target_entry_ids(db, target, semester.id)
    entries = {
        e.id: e
        for e in db.scalars(select(ScheduleEntry).where(ScheduleEntry.id.in_(entry_ids)))
    }
    exceptions: dict[int, list[ScheduleException]] = {}
    for exc in db.scalars(
        select(ScheduleException).where(ScheduleException.entry_id.in_(entry_ids))
    ):
        exceptions.setdefault(exc.entry_id, []).append(exc)
    return _Lookups(db), entries, exceptions


def _collect_day(
    day: date,
    week: calendar_service.WeekPlan,
    semester: Semester,
    entries: dict[int, ScheduleEntry],
    exceptions: dict[int, list[ScheduleException]],
    lookups: _Lookups,
    calendar_exceptions: list[CalendarException],
    subgroup_id: int | None,
) -> DayView:
    closed = _closed_reason(calendar_exceptions, day)
    if closed is not None:
        return DayView(
            day=day,
            day_of_week=day.isoweekday(),
            semester_id=semester.id,
            semester_name=semester.name,
            week_number=week.number,
            parity=week.parity,
            is_working=False,
            closed_reason=closed,
            lessons=[],
        )

    note = _day_note(calendar_exceptions, day)
    lessons: list[LessonView] = []
    for entry in entries.values():
        if not _matches_subgroup(entry, subgroup_id):
            continue
        lesson = _resolve_occurrence(
            entry, day, week.parity, exceptions.get(entry.id, []), lookups, note
        )
        if lesson is not None:
            lessons.append(lesson)

    lessons.sort(key=lambda l: (l.pair_number, l.subject_name))
    return DayView(
        day=day,
        day_of_week=day.isoweekday(),
        semester_id=semester.id,
        semester_name=semester.name,
        week_number=week.number,
        parity=week.parity,
        is_working=True,
        closed_reason=None,
        lessons=lessons,
    )


def _empty_day(day: date, semester: Semester | None, reason: str) -> DayView:
    return DayView(
        day=day,
        day_of_week=day.isoweekday(),
        semester_id=semester.id if semester else None,
        semester_name=semester.name if semester else None,
        week_number=None,
        parity=None,
        is_working=False,
        closed_reason=reason,
        lessons=[],
    )


def _calendar_exceptions(db: Session, semester_id: int) -> list[CalendarException]:
    return list(
        db.scalars(select(CalendarException).where(CalendarException.semester_id == semester_id))
    )


def day_state(db: Session, semester: Semester, day: date) -> tuple[bool, str | None]:
    """Чи є день навчальним і чому ні (свято, канікули) — без вибірки занять."""
    closed = _closed_reason(_calendar_exceptions(db, semester.id), day)
    return closed is None, closed


def day_view(
    db: Session,
    *,
    target: Target,
    day: date,
    semester_id: int | None = None,
    subgroup_id: int | None = None,
) -> DayView:
    semester = resolve_semester(db, day, semester_id)
    if semester is None:
        return _empty_day(day, None, "Дата поза межами семестру")

    week = calendar_service.week_for_date(semester, day)
    if week is None:
        return _empty_day(day, semester, "Дата поза межами семестру")

    lookups, entries, exceptions = _load_context(db, target, semester)
    return _collect_day(
        day,
        week,
        semester,
        entries,
        exceptions,
        lookups,
        _calendar_exceptions(db, semester.id),
        subgroup_id,
    )


def week_view(
    db: Session,
    *,
    target: Target,
    day: date,
    semester_id: int | None = None,
    subgroup_id: int | None = None,
) -> WeekView:
    """Тиждень Пн-Нд, що містить дату. Сб і Нд показуються лише за потреби."""
    monday = monday_of(day)
    sunday = monday + timedelta(days=6)

    semester = resolve_semester(db, day, semester_id)
    if semester is None:
        return WeekView(
            starts_on=monday,
            ends_on=sunday,
            semester_id=None,
            semester_name=None,
            week_number=None,
            parity=None,
            days=[],
        )

    lookups, entries, exceptions = _load_context(db, target, semester)
    calendar_exceptions = _calendar_exceptions(db, semester.id)

    days: list[DayView] = []
    week_number: int | None = None
    parity: Parity | None = None

    for offset in range(7):
        current = monday + timedelta(days=offset)
        week = calendar_service.week_for_date(semester, current)
        if week is None:
            continue
        if week_number is None:
            week_number, parity = week.number, week.parity

        view = _collect_day(
            current,
            week,
            semester,
            entries,
            exceptions,
            lookups,
            calendar_exceptions,
            subgroup_id,
        )
        # Пн-Пт у сітці завжди (навіть закриті святом — зі зрозумілою причиною),
        # вихідні — лише якщо того дня є заняття, як і в Excel-експорті.
        if view.day_of_week <= 5 or view.lessons:
            days.append(view)

    return WeekView(
        starts_on=monday,
        ends_on=sunday,
        semester_id=semester.id,
        semester_name=semester.name,
        week_number=week_number,
        parity=parity,
        days=days,
    )
