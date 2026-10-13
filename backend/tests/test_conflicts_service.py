import pytest

from app.models import (
    ConflictSeverity,
    Parity,
    ScheduleEntry,
    ScheduleGroup,
    ScheduleRoom,
    ScheduleTeacher,
)
from app.services.conflicts import detect_conflicts, parity_overlaps


@pytest.mark.parametrize(
    "a,b,expected",
    [
        (Parity.ODD, Parity.ODD, True),
        (Parity.EVEN, Parity.EVEN, True),
        (Parity.ODD, Parity.EVEN, False),
        (Parity.EVEN, Parity.ODD, False),
        (Parity.BOTH, Parity.ODD, True),
        (Parity.BOTH, Parity.EVEN, True),
        (Parity.BOTH, Parity.BOTH, True),
    ],
)
def test_parity_table(a, b, expected):
    assert parity_overlaps(a, b) is expected


def _entry(db, parity, *, teachers=(), rooms=(), groups=(), day=1, pair=1, semester_id=1):
    entry = ScheduleEntry(
        semester_id=semester_id,
        subject_id=1,
        lesson_type_id=1,
        pair_time_id=pair,
        day_of_week=day,
        week_parity=parity,
    )
    entry.teachers = [ScheduleTeacher(teacher_id=t) for t in teachers]
    entry.rooms = [ScheduleRoom(room_id=r) for r in rooms]
    entry.groups = [ScheduleGroup(group_id=g) for g in groups]
    db.add(entry)
    db.flush()
    return entry


def test_same_room_same_parity_is_error(db):
    _entry(db, Parity.ODD, rooms=[10])
    new = _entry(db, Parity.ODD, rooms=[10])
    conflicts = detect_conflicts(db, new)
    assert len(conflicts) == 1
    assert conflicts[0].severity is ConflictSeverity.ERROR
    assert conflicts[0].resource_id == 10


def test_odd_and_even_do_not_conflict(db):
    _entry(db, Parity.ODD, rooms=[10], teachers=[5])
    new = _entry(db, Parity.EVEN, rooms=[10], teachers=[5])
    assert detect_conflicts(db, new) == []


def test_both_conflicts_with_odd(db):
    _entry(db, Parity.ODD, teachers=[7])
    new = _entry(db, Parity.BOTH, teachers=[7])
    conflicts = detect_conflicts(db, new)
    assert len(conflicts) == 1
    assert conflicts[0].resource_id == 7


def test_group_overlap_is_warning_not_error(db):
    _entry(db, Parity.ODD, groups=[3])
    new = _entry(db, Parity.ODD, groups=[3])
    conflicts = detect_conflicts(db, new)
    assert len(conflicts) == 1
    assert conflicts[0].severity is ConflictSeverity.WARNING


def test_different_pair_no_conflict(db):
    _entry(db, Parity.ODD, rooms=[10], pair=1)
    new = _entry(db, Parity.ODD, rooms=[10], pair=2)
    assert detect_conflicts(db, new) == []


def test_different_day_no_conflict(db):
    _entry(db, Parity.ODD, rooms=[10], day=1)
    new = _entry(db, Parity.ODD, rooms=[10], day=2)
    assert detect_conflicts(db, new) == []


def test_different_semester_no_conflict(db):
    _entry(db, Parity.ODD, rooms=[10], semester_id=1)
    new = _entry(db, Parity.ODD, rooms=[10], semester_id=2)
    assert detect_conflicts(db, new) == []


def test_multiple_shared_resources_reported_separately(db):
    _entry(db, Parity.ODD, teachers=[1], rooms=[2])
    new = _entry(db, Parity.ODD, teachers=[1], rooms=[2])
    conflicts = detect_conflicts(db, new)
    kinds = {c.kind.value for c in conflicts}
    assert kinds == {"TEACHER", "ROOM"}
