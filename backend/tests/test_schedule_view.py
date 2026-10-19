"""Розгортання шаблону розкладу на конкретні дати."""

from datetime import date

from sqlalchemy.orm import Session

from app.models import (
    CalendarException,
    ExceptionAction,
    ExceptionKind,
    Parity,
    ScheduleEntry,
    ScheduleException,
    ScheduleGroup,
    ScheduleRoom,
    ScheduleStream,
    ScheduleSubgroup,
    ScheduleTeacher,
    Stream,
    StreamGroup,
    Subgroup,
    Teacher,
)
from app.services.schedule_view import (
    LessonStatus,
    Target,
    TargetKind,
    day_view,
    week_view,
)

# Семестр фікстури `reference` починається 01.09.2025 (понеділок):
# тиждень 1 — 01-07.09 (ODD), тиждень 2 — 08-14.09 (EVEN).
MONDAY_ODD = date(2025, 9, 1)
MONDAY_EVEN = date(2025, 9, 8)
WEDNESDAY_ODD = date(2025, 9, 3)


def _entry(
    db: Session,
    ref: dict,
    *,
    day_of_week: int = 1,
    parity: Parity = Parity.BOTH,
    pair: str = "pair1",
    group_ids: list[int] | None = None,
    subgroup_ids: list[int] | None = None,
    stream_ids: list[int] | None = None,
    teacher_ids: list[int] | None = None,
) -> ScheduleEntry:
    entry = ScheduleEntry(
        semester_id=ref["semester"],
        subject_id=ref["subject"],
        lesson_type_id=ref["lesson_type"],
        pair_time_id=ref[pair],
        day_of_week=day_of_week,
        week_parity=parity,
    )
    entry.groups = [ScheduleGroup(group_id=g) for g in (group_ids or [])]
    entry.subgroups = [ScheduleSubgroup(subgroup_id=s) for s in (subgroup_ids or [])]
    entry.streams = [ScheduleStream(stream_id=s) for s in (stream_ids or [])]
    entry.teachers = [ScheduleTeacher(teacher_id=t) for t in (teacher_ids or [ref["teacher"]])]
    entry.rooms = [ScheduleRoom(room_id=ref["room"])]
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def _group_target(ref: dict) -> Target:
    return Target(kind=TargetKind.GROUP, id=ref["group1"])


def test_parity_decides_whether_lesson_happens(db: Session, reference):
    _entry(db, reference, parity=Parity.ODD, group_ids=[reference["group1"]])

    odd = day_view(db, target=_group_target(reference), day=MONDAY_ODD)
    even = day_view(db, target=_group_target(reference), day=MONDAY_EVEN)

    assert odd.week_number == 1 and odd.parity is Parity.ODD
    assert [l.subject_name for l in odd.lessons] == ["Математичний аналіз"]
    assert even.week_number == 2 and even.parity is Parity.EVEN
    assert even.lessons == []


def test_both_parity_lesson_happens_every_week(db: Session, reference):
    _entry(db, reference, parity=Parity.BOTH, group_ids=[reference["group1"]])

    for day in (MONDAY_ODD, MONDAY_EVEN):
        view = day_view(db, target=_group_target(reference), day=day)
        assert len(view.lessons) == 1


def test_lesson_is_denormalized_for_display(db: Session, reference):
    _entry(db, reference, group_ids=[reference["group1"]])

    lesson = day_view(db, target=_group_target(reference), day=MONDAY_ODD).lessons[0]

    assert lesson.subject_name == "Математичний аналіз"
    assert lesson.lesson_type_name == "Лекція"
    assert [t.short_name for t in lesson.teachers] == ["Іваненко І."]
    assert [r.number for r in lesson.rooms] == ["А.203"]
    assert lesson.groups == ["121"]
    assert lesson.status is LessonStatus.NORMAL


def test_subgroup_filter_hides_other_subgroup(db: Session, reference):
    first = Subgroup(group_id=reference["group1"], name="1")
    second = Subgroup(group_id=reference["group1"], name="2")
    db.add_all([first, second])
    db.commit()

    _entry(db, reference, subgroup_ids=[first.id])
    _entry(db, reference, pair="pair2", subgroup_ids=[second.id])
    _entry(db, reference, day_of_week=2, group_ids=[reference["group1"]])

    view = day_view(db, target=_group_target(reference), day=MONDAY_ODD, subgroup_id=first.id)
    assert [l.subgroups for l in view.lessons] == [["1"]]

    # Без фільтра підгрупи видно обидві лабораторні.
    both = day_view(db, target=_group_target(reference), day=MONDAY_ODD)
    assert len(both.lessons) == 2


def test_whole_group_lesson_visible_with_subgroup_filter(db: Session, reference):
    subgroup = Subgroup(group_id=reference["group1"], name="1")
    db.add(subgroup)
    db.commit()
    _entry(db, reference, group_ids=[reference["group1"]])

    view = day_view(db, target=_group_target(reference), day=MONDAY_ODD, subgroup_id=subgroup.id)
    assert len(view.lessons) == 1


def test_stream_lesson_reaches_member_group(db: Session, reference):
    stream = Stream(name="КН-3")
    db.add(stream)
    db.flush()
    db.add(StreamGroup(stream_id=stream.id, group_id=reference["group1"]))
    db.commit()
    _entry(db, reference, stream_ids=[stream.id])

    view = day_view(db, target=_group_target(reference), day=MONDAY_ODD)
    assert [l.streams for l in view.lessons] == [["КН-3"]]


def test_holiday_closes_the_day(db: Session, reference):
    _entry(db, reference, group_ids=[reference["group1"]])
    db.add(
        CalendarException(
            semester_id=reference["semester"],
            kind=ExceptionKind.HOLIDAY,
            date_from=MONDAY_ODD,
            date_to=MONDAY_ODD,
            description="День знань",
        )
    )
    db.commit()

    view = day_view(db, target=_group_target(reference), day=MONDAY_ODD)
    assert view.is_working is False
    assert view.closed_reason == "День знань"
    assert view.lessons == []


def test_cancelled_lesson_is_shown_with_reason(db: Session, reference):
    entry = _entry(db, reference, group_ids=[reference["group1"]])
    db.add(
        ScheduleException(
            entry_id=entry.id,
            action=ExceptionAction.CANCEL,
            on_date=MONDAY_ODD,
            reason="Семінар кафедри",
        )
    )
    db.commit()

    cancelled = day_view(db, target=_group_target(reference), day=MONDAY_ODD).lessons[0]
    assert cancelled.status is LessonStatus.CANCELLED
    assert cancelled.change_reason == "Семінар кафедри"

    # Наступного тижня заняття відбувається як завжди.
    next_week = day_view(db, target=_group_target(reference), day=MONDAY_EVEN).lessons[0]
    assert next_week.status is LessonStatus.NORMAL


def test_move_to_another_date_shows_on_both_days(db: Session, reference):
    entry = _entry(db, reference, group_ids=[reference["group1"]])
    db.add(
        ScheduleException(
            entry_id=entry.id,
            action=ExceptionAction.MOVE,
            on_date=MONDAY_ODD,
            new_date=WEDNESDAY_ODD,
            new_pair_time_id=reference["pair2"],
            reason="Перенесення",
        )
    )
    db.commit()

    source = day_view(db, target=_group_target(reference), day=MONDAY_ODD).lessons[0]
    assert source.status is LessonStatus.MOVED_OUT
    assert source.moved_to == WEDNESDAY_ODD

    target = day_view(db, target=_group_target(reference), day=WEDNESDAY_ODD).lessons[0]
    assert target.status is LessonStatus.MOVED_IN
    assert target.moved_from == MONDAY_ODD
    assert target.pair_number == 2


def test_teacher_replacement_shows_substitute(db: Session, reference):
    substitute = Teacher(first_name="Олена", last_name="Петренко", short_name="Петренко О.")
    db.add(substitute)
    db.flush()
    entry = _entry(db, reference, group_ids=[reference["group1"]])
    db.add(
        ScheduleException(
            entry_id=entry.id,
            action=ExceptionAction.REPLACE,
            on_date=MONDAY_ODD,
            new_teacher_id=substitute.id,
            reason="Відрядження",
        )
    )
    db.commit()

    lesson = day_view(db, target=_group_target(reference), day=MONDAY_ODD).lessons[0]
    assert lesson.status is LessonStatus.REPLACED
    assert [t.short_name for t in lesson.teachers] == ["Петренко О."]
    assert lesson.teachers[0].is_substitute is True

    # Заміна бачить пару у своєму розкладі.
    substitute_view = day_view(
        db, target=Target(kind=TargetKind.TEACHER, id=substitute.id), day=MONDAY_ODD
    )
    assert len(substitute_view.lessons) == 1


def test_week_view_keeps_workdays_and_adds_saturday_only_when_needed(db: Session, reference):
    _entry(db, reference, group_ids=[reference["group1"]])

    plain = week_view(db, target=_group_target(reference), day=MONDAY_ODD)
    assert [d.day_of_week for d in plain.days] == [1, 2, 3, 4, 5]
    assert plain.week_number == 1

    saturday_entry = _entry(db, reference, day_of_week=6, group_ids=[reference["group1"]])
    assert saturday_entry.day_of_week == 6
    with_saturday = week_view(db, target=_group_target(reference), day=MONDAY_ODD)
    assert [d.day_of_week for d in with_saturday.days] == [1, 2, 3, 4, 5, 6]


def test_date_outside_semester_is_reported(db: Session, reference):
    view = day_view(db, target=_group_target(reference), day=date(2026, 7, 1))
    assert view.is_working is False
    assert view.closed_reason == "Дата поза межами семестру"
    assert view.week_number is None
