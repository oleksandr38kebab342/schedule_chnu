"""Демонстраційний набір даних: факультет, кафедри, викладачі, групи, розклад.

Потрібен, щоб фронтенд і демо запускалися на осмислених даних, а не на
порожній базі. Запуск (після `python -m scripts.seed`):

    python -m scripts.seed_demo

Скрипт ідемпотентний: довідники оновлюються за натуральними ключами, а
заняття демонстраційного семестру перезаписуються. Навчальний рік рахується
від поточної дати, тому демо завжди показує «живий» семестр.
"""

import os
import sys
from datetime import date, time, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import permissions as perm
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import (
    AcademicYear,
    Building,
    CalendarException,
    Department,
    ExceptionAction,
    ExceptionKind,
    Faculty,
    Group,
    LessonType,
    PairTime,
    Parity,
    Role,
    Room,
    RoomAlias,
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
    SubjectDepartment,
    Teacher,
    TeacherDepartment,
    User,
    UserRole,
    normalize_room_code,
)
from app.services import calendar as calendar_service

DEMO_PASSWORD = os.environ.get("DEMO_PASSWORD", "demo12345")

PAIR_TIMES = [
    (1, time(8, 30), time(10, 5)),
    (2, time(10, 25), time(12, 0)),
    (3, time(12, 20), time(13, 55)),
    (4, time(14, 15), time(15, 50)),
    (5, time(16, 10), time(17, 45)),
    (6, time(18, 0), time(19, 35)),
]

LESSON_TYPES = [
    ("LEC", "Лекція", "Лк"),
    ("LAB", "Лабораторна", "Лб"),
    ("PRACT", "Практика", "Пр"),
    ("ELECT", "Факультатив", "Фк"),
]

SUBJECTS = [
    ("ASD", "Архітектура програмного забезпечення", "Архітектура ПЗ"),
    ("SEC", "Безпека програмних систем", "Безпека ПС"),
    ("DB", "Бази даних", "Бази даних"),
    ("ALG", "Алгоритми та структури даних", "Алгоритми"),
    ("WEB", "Веб-технології", "Веб-технології"),
    ("OS", "Операційні системи", "ОС"),
    ("DM", "Дискретна математика", "Дискретна мат."),
    ("ENG", "Англійська мова за професійним спрямуванням", "Англійська"),
    ("SPORT", "Військова підготовка / Спорт", "Спорт"),
]

TEACHERS = [
    ("Мельник", "Василь", "Петрович", "проф. Мельник В. П.", "д-р техн. наук", "професор", "CS"),
    ("Коваленко", "Оксана", "Миколаївна", "доц. Коваленко О. М.", "канд. техн. наук", "доцент", "CS"),
    ("Ткаченко", "Андрій", "Ігорович", "доц. Ткаченко А. І.", "канд. техн. наук", "доцент", "SE"),
    ("Сидоренко", "Ірина", "Василівна", "ст. викл. Сидоренко І. В.", None, "старший викладач", "SE"),
    ("Бондар", "Петро", "Олексійович", "асист. Бондар П. О.", None, "асистент", "CS"),
    ("Гриценко", "Наталія", "Степанівна", "доц. Гриценко Н. С.", "канд. філол. наук", "доцент", "LANG"),
    ("Левчук", "Сергій", "Вікторович", "ст. викл. Левчук С. В.", None, "старший викладач", "PE"),
]

DEPARTMENTS = [
    ("CS", "Кафедра комп'ютерних наук", "Комп'ютерних наук"),
    ("SE", "Кафедра програмного забезпечення комп'ютерних систем", "Програмного забезпечення"),
    ("LANG", "Кафедра іноземних мов для природничих факультетів", "Іноземних мов"),
    ("PE", "Кафедра фізичного виховання", "Фізичного виховання"),
]

BUILDINGS = [
    ("A", "Головний корпус", "вул. Коцюбинського, 2"),
    ("B", "Корпус 5", "вул. Університетська, 28"),
    ("S", "Спорткомплекс", "вул. Небесної Сотні, 7"),
]

# (корпус, номер, тип, поверх, місткість, синоніми)
ROOMS = [
    ("A", "А.402", "Лекційна", 4, 120, ["А402", "А-402"]),
    ("A", "А.203А", "Семінарська", 2, 40, ["А203А", "А-203А"]),
    ("B", "Б.215", "Комп'ютерний клас", 2, 24, ["Б215", "Б-215"]),
    ("B", "Б.101", "Лекційна", 1, 90, ["Б101"]),
    ("B", "Б.304", "Комп'ютерний клас", 3, 20, ["Б304"]),
    ("S", "Зал № 2", "Спортивна зала", 1, 60, ["Зал 2", "зал№2"]),
]

GROUPS = [
    ("КН-321", "CS", 3, 26),
    ("КН-322", "CS", 3, 24),
    ("КН-323", "CS", 3, 25),
    ("ПЗ-321", "SE", 3, 22),
    ("КН-421", "CS", 4, 19),
]

# Розклад групи КН-321 та потоку КН-3 на тиждень.
# (день, пара, парність, дисципліна, тип, викладач, аудиторія, аудиторія-слухачі)
LESSONS = [
    # Понеділок
    (1, 1, "ODD", "ALG", "PRACT", "Ткаченко", "Б.101", {"groups": ["КН-321"]}),
    (1, 2, "BOTH", "DB", "LEC", "Сидоренко", "А.402", {"streams": ["КН-3"]}),
    (1, 3, "ODD", "DB", "LAB", "Бондар", "Б.215", {"subgroups": [("КН-321", "1")]}),
    (1, 3, "EVEN", "DB", "LAB", "Бондар", "Б.215", {"subgroups": [("КН-321", "2")]}),
    # Вівторок
    (2, 2, "BOTH", "OS", "LEC", "Коваленко", "А.402", {"streams": ["КН-3"]}),
    (2, 3, "BOTH", "ENG", "PRACT", "Гриценко", "А.203А", {"subgroups": [("КН-321", "1")]}),
    (2, 4, "BOTH", "ENG", "PRACT", "Гриценко", "А.203А", {"subgroups": [("КН-321", "2")]}),
    # Середа — день з референсного макета
    (3, 1, "BOTH", "ASD", "LEC", "Мельник", "А.402", {"streams": ["КН-3"]}),
    (3, 2, "BOTH", "ASD", "LEC", "Мельник", "А.402", {"streams": ["КН-3"]}),
    (3, 3, "ODD", "SEC", "LAB", "Ткаченко", "Б.215", {"subgroups": [("КН-321", "1")]}),
    (3, 3, "EVEN", "SEC", "LAB", "Ткаченко", "Б.215", {"subgroups": [("КН-321", "2")]}),
    (3, 4, "BOTH", "SPORT", "ELECT", "Левчук", "Зал № 2", {"groups": ["КН-321"]}),
    # Четвер
    (4, 1, "BOTH", "WEB", "LEC", "Коваленко", "А.402", {"streams": ["КН-3"]}),
    (4, 2, "ODD", "WEB", "LAB", "Бондар", "Б.304", {"subgroups": [("КН-321", "1")]}),
    (4, 2, "EVEN", "WEB", "LAB", "Бондар", "Б.304", {"subgroups": [("КН-321", "2")]}),
    (4, 3, "BOTH", "DM", "PRACT", "Сидоренко", "А.203А", {"groups": ["КН-321"]}),
    # П'ятниця
    (5, 2, "BOTH", "SEC", "LEC", "Мельник", "А.402", {"streams": ["КН-3"]}),
    (5, 3, "ODD", "ALG", "PRACT", "Ткаченко", "Б.101", {"groups": ["КН-321"]}),
    # Сусідні групи, щоб аудиторії й викладачі були зайняті не лише в КН-321
    (1, 1, "BOTH", "OS", "PRACT", "Коваленко", "Б.304", {"groups": ["КН-421"]}),
    (2, 1, "BOTH", "WEB", "PRACT", "Бондар", "Б.101", {"groups": ["ПЗ-321"]}),
    (4, 4, "BOTH", "DB", "PRACT", "Сидоренко", "Б.101", {"groups": ["КН-322"]}),
]

DEMO_USERS = [
    ("dispatcher@chnu.edu.ua", "Марина Диспетчер", perm.DISPATCHER),
    ("teacher@chnu.edu.ua", "Олег Викладач", perm.TEACHER),
    ("student@chnu.edu.ua", "Софія Студентка", perm.STUDENT),
]


def academic_year_bounds(today: date) -> tuple[str, date, date]:
    """Навчальний рік, у якому ми зараз: з 1 липня починається наступний."""
    start_year = today.year if today.month >= 7 else today.year - 1
    return (
        f"{start_year}/{start_year + 1}",
        date(start_year, 9, 1),
        date(start_year + 1, 6, 30),
    )


def semester_bounds(today: date, start_year: int) -> tuple[int, str, date, date]:
    """Семестр для поточної дати; поза навчанням — найближчий майбутній."""
    first = (1, "I семестр", date(start_year, 9, 1), date(start_year + 1, 1, 10))
    second = (2, "II семестр", date(start_year + 1, 2, 1), date(start_year + 1, 6, 20))
    if first[2] <= today <= first[3]:
        return first
    if second[2] <= today <= second[3]:
        return second
    return first if today < first[2] else second


def get_or_create(db: Session, model, defaults: dict | None = None, **filters):
    stmt = select(model)
    for field, value in filters.items():
        stmt = stmt.where(getattr(model, field) == value)
    obj = db.scalar(stmt)
    if obj is None:
        obj = model(**filters, **(defaults or {}))
        db.add(obj)
        db.flush()
    elif defaults:
        for field, value in defaults.items():
            setattr(obj, field, value)
    return obj


def seed_reference(db: Session) -> dict:
    faculty = get_or_create(
        db,
        Faculty,
        {"name": "Факультет математики та інформатики", "short_name": "ФМІ"},
        code="FMI",
    )

    departments = {
        code: get_or_create(
            db, Department, {"name": name, "short_name": short, "faculty_id": faculty.id}, code=code
        )
        for code, name, short in DEPARTMENTS
    }

    teachers: dict[str, Teacher] = {}
    for last, first, middle, short, degree, position, dept_code in TEACHERS:
        teacher = db.scalar(
            select(Teacher).where(Teacher.last_name == last, Teacher.first_name == first)
        )
        if teacher is None:
            teacher = Teacher(last_name=last, first_name=first)
            db.add(teacher)
        teacher.middle_name = middle
        teacher.short_name = short
        teacher.degree = degree
        teacher.position = position
        db.flush()
        department = departments[dept_code]
        if not any(l.department_id == department.id for l in teacher.department_links):
            db.add(
                TeacherDepartment(
                    teacher_id=teacher.id, department_id=department.id, is_primary=True
                )
            )
        teachers[last] = teacher

    lesson_types = {
        code: get_or_create(db, LessonType, {"name": name, "short_name": short}, code=code)
        for code, name, short in LESSON_TYPES
    }

    subjects: dict[str, Subject] = {}
    for code, name, short in SUBJECTS:
        subject = get_or_create(db, Subject, {"name": name, "short_name": short}, code=code)
        if not subject.department_links:
            db.add(SubjectDepartment(subject_id=subject.id, department_id=departments["CS"].id))
        subjects[code] = subject

    buildings = {
        code: get_or_create(db, Building, {"name": name, "address": address}, code=code)
        for code, name, address in BUILDINGS
    }

    rooms: dict[str, Room] = {}
    for building_code, number, room_type, floor, capacity, aliases in ROOMS:
        building = buildings[building_code]
        room = db.scalar(
            select(Room).where(
                Room.building_id == building.id, Room.normalized == normalize_room_code(number)
            )
        )
        if room is None:
            room = Room(
                building_id=building.id, number=number, normalized=normalize_room_code(number)
            )
            db.add(room)
        room.room_type = room_type
        room.floor = floor
        room.capacity = capacity
        db.flush()
        known = {a.normalized for a in room.aliases}
        for alias in aliases:
            if normalize_room_code(alias) not in known:
                db.add(
                    RoomAlias(room_id=room.id, alias=alias, normalized=normalize_room_code(alias))
                )
        rooms[number] = room

    pairs = {
        number: get_or_create(db, PairTime, {"starts_at": starts, "ends_at": ends}, number=number)
        for number, starts, ends in PAIR_TIMES
    }

    groups: dict[str, Group] = {}
    subgroups: dict[tuple[str, str], Subgroup] = {}
    for name, dept_code, course, students in GROUPS:
        group = get_or_create(
            db,
            Group,
            {"department_id": departments[dept_code].id, "course": course, "students_count": students},
            name=name,
        )
        groups[name] = group
        for sub_name in ("1", "2"):
            subgroups[(name, sub_name)] = get_or_create(
                db, Subgroup, None, group_id=group.id, name=sub_name
            )

    stream = get_or_create(db, Stream, None, name="КН-3")
    for group_name in ("КН-321", "КН-322", "КН-323"):
        get_or_create(
            db, StreamGroup, None, stream_id=stream.id, group_id=groups[group_name].id
        )

    db.commit()
    return {
        "faculty": faculty,
        "departments": departments,
        "teachers": teachers,
        "lesson_types": lesson_types,
        "subjects": subjects,
        "rooms": rooms,
        "pairs": pairs,
        "groups": groups,
        "subgroups": subgroups,
        "streams": {"КН-3": stream},
    }


def seed_calendar(db: Session, today: date) -> Semester:
    name, year_start, year_end = academic_year_bounds(today)
    year = get_or_create(db, AcademicYear, {"starts_on": year_start, "ends_on": year_end}, name=name)

    ordinal, sem_name, start, end = semester_bounds(today, year_start.year)
    semester = get_or_create(
        db,
        Semester,
        {
            "name": sem_name,
            "start_date": start,
            "end_date": end,
            "first_week_parity": Parity.ODD,
        },
        academic_year_id=year.id,
        ordinal=ordinal,
    )
    db.flush()

    # Тижні перегенеровуємо: межі семестру могли змінитися.
    for week in list(semester.weeks):
        db.delete(week)
    db.flush()
    db.add_all(calendar_service.generate_weeks(semester))
    db.commit()
    return semester


def seed_schedule(db: Session, ref: dict, semester: Semester) -> tuple[int, dict]:
    """Перезаписує заняття демонстраційного семестру."""
    for entry in db.scalars(
        select(ScheduleEntry).where(ScheduleEntry.semester_id == semester.id)
    ):
        db.delete(entry)
    db.flush()

    created: dict[tuple, ScheduleEntry] = {}
    for day, pair, parity, subject_code, type_code, teacher_last, room_number, audience in LESSONS:
        entry = ScheduleEntry(
            semester_id=semester.id,
            subject_id=ref["subjects"][subject_code].id,
            lesson_type_id=ref["lesson_types"][type_code].id,
            pair_time_id=ref["pairs"][pair].id,
            day_of_week=day,
            week_parity=Parity(parity),
        )
        entry.teachers = [ScheduleTeacher(teacher_id=ref["teachers"][teacher_last].id)]
        entry.rooms = [ScheduleRoom(room_id=ref["rooms"][room_number].id)]
        entry.groups = [
            ScheduleGroup(group_id=ref["groups"][name].id) for name in audience.get("groups", [])
        ]
        entry.subgroups = [
            ScheduleSubgroup(subgroup_id=ref["subgroups"][key].id)
            for key in audience.get("subgroups", [])
        ]
        entry.streams = [
            ScheduleStream(stream_id=ref["streams"][name].id) for name in audience.get("streams", [])
        ]
        db.add(entry)
        db.flush()
        created[(day, pair, parity, subject_code)] = entry

    db.commit()
    return len(created), created


def _next_weekday(start: date, weekday: int) -> date:
    """Найближча дата з потрібним днем тижня (1=Пн), починаючи зі start."""
    delta = (weekday - start.isoweekday()) % 7
    return start + timedelta(days=delta)


def seed_changes(
    db: Session, ref: dict, semester: Semester, entries: dict, today: date
) -> int:
    """Заміна, скасування і перенесення — щоб у демо було видно всі статуси."""
    anchor = max(today, semester.start_date)
    if anchor > semester.end_date:
        return 0

    wednesday = _next_weekday(anchor, 3)
    thursday = _next_weekday(anchor, 4)
    friday = _next_weekday(anchor, 5)
    saturday = thursday + timedelta(days=2)
    if max(wednesday, friday) > semester.end_date:
        return 0

    week = calendar_service.week_for_date(semester, wednesday)
    parity = week.parity.value if week else "ODD"

    planned: list[ScheduleException] = []
    lab = entries.get((3, 3, parity, "SEC"))
    if lab is not None:
        planned.append(
            ScheduleException(
                entry_id=lab.id,
                action=ExceptionAction.REPLACE,
                on_date=wednesday,
                new_teacher_id=ref["teachers"]["Коваленко"].id,
                reason="Основний викладач у відрядженні",
            )
        )

    moved = entries.get((4, 3, "BOTH", "DM"))
    if moved is not None and saturday <= semester.end_date:
        planned.append(
            ScheduleException(
                entry_id=moved.id,
                action=ExceptionAction.MOVE,
                on_date=thursday,
                new_date=saturday,
                new_pair_time_id=ref["pairs"][2].id,
                reason="Перенесення на робочу суботу",
            )
        )
        get_or_create(
            db,
            CalendarException,
            {"description": "Робоча субота (відпрацювання)"},
            semester_id=semester.id,
            kind=ExceptionKind.WORKING_DAY,
            date_from=saturday,
            date_to=saturday,
        )

    cancelled = entries.get((5, 2, "BOTH", "SEC"))
    if cancelled is not None:
        planned.append(
            ScheduleException(
                entry_id=cancelled.id,
                action=ExceptionAction.CANCEL,
                on_date=friday,
                reason="Науковий семінар кафедри",
            )
        )

    for exception in planned:
        exists = db.scalar(
            select(ScheduleException).where(
                ScheduleException.entry_id == exception.entry_id,
                ScheduleException.on_date == exception.on_date,
                ScheduleException.action == exception.action,
            )
        )
        if exists is None:
            db.add(exception)

    # Державне свято в межах семестру — день без занять.
    holiday = date(semester.start_date.year, 10, 14)
    if semester.start_date <= holiday <= semester.end_date:
        get_or_create(
            db,
            CalendarException,
            {"description": "День захисників і захисниць України"},
            semester_id=semester.id,
            kind=ExceptionKind.HOLIDAY,
            date_from=holiday,
            date_to=holiday,
        )

    db.commit()
    return len(planned)


def seed_users(db: Session) -> list[str]:
    roles = {r.code: r for r in db.scalars(select(Role))}
    created: list[str] = []
    for email, full_name, role_code in DEMO_USERS:
        role = roles.get(role_code)
        if role is None:
            continue
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(
                email=email,
                full_name=full_name,
                password_hash=hash_password(DEMO_PASSWORD),
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id))
            created.append(email)
    db.commit()
    return created


def main() -> None:
    # Консоль Windows стартує в cp1252 і падає на кириличному виводі.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    today = date.today()

    with SessionLocal() as db:
        ref = seed_reference(db)
        semester = seed_calendar(db, today)
        lessons, entries = seed_schedule(db, ref, semester)
        changes = seed_changes(db, ref, semester, entries, today)
        users = seed_users(db)

    print(f"Семестр: {semester.name} ({semester.start_date} — {semester.end_date})")
    print(f"Груп: {len(GROUPS)}, викладачів: {len(TEACHERS)}, занять: {lessons}")
    print(f"Точкових змін (заміна/перенесення/скасування): {changes}")
    if users:
        print("Демо-користувачі (пароль DEMO_PASSWORD, типово demo12345):")
        for email in users:
            print(f"  {email}")
    else:
        print("Демо-користувачі вже існують.")


if __name__ == "__main__":
    main()
