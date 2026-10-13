from datetime import date

from app.models import Parity, Semester
from app.services import calendar as cal


def _semester(start: date, end: date, first: Parity = Parity.ODD) -> Semester:
    return Semester(
        id=1,
        academic_year_id=1,
        ordinal=1,
        name="Тест",
        start_date=start,
        end_date=end,
        first_week_parity=first,
    )


def test_first_week_is_one_and_odd():
    """DoD: 01.09 -> тиждень 1; 07.09 того ж тижня -> теж тиждень 1."""
    sem = _semester(date(2025, 9, 1), date(2025, 12, 28))  # 1 вересня — понеділок
    assert cal.week_for_date(sem, date(2025, 9, 1)).number == 1
    assert cal.week_for_date(sem, date(2025, 9, 7)).number == 1
    assert cal.week_for_date(sem, date(2025, 9, 1)).parity is Parity.ODD


def test_second_week_is_even():
    sem = _semester(date(2025, 9, 1), date(2025, 12, 28))
    wk = cal.week_for_date(sem, date(2025, 9, 8))
    assert wk.number == 2
    assert wk.parity is Parity.EVEN


def test_week_numbering_restarts_each_semester():
    """DoD: ІІ семестр завжди починається з тижня 1, незалежно від І."""
    second = _semester(date(2026, 2, 9), date(2026, 5, 31))
    assert cal.week_for_date(second, date(2026, 2, 9)).number == 1
    assert cal.week_for_date(second, date(2026, 2, 9)).parity is Parity.ODD


def test_date_outside_semester_returns_none():
    sem = _semester(date(2025, 9, 1), date(2025, 12, 28))
    assert cal.week_for_date(sem, date(2025, 8, 31)) is None
    assert cal.week_for_date(sem, date(2026, 1, 1)) is None


def test_generated_weeks_cover_whole_semester():
    sem = _semester(date(2025, 9, 1), date(2025, 12, 28))
    plans = cal.plan_weeks(sem)
    assert plans[0].number == 1
    assert plans[0].starts_on == date(2025, 9, 1)
    assert plans[-1].ends_on == date(2025, 12, 28)
    # Номери йдуть підряд, парність чергується.
    assert [p.number for p in plans] == list(range(1, len(plans) + 1))
    for prev, nxt in zip(plans, plans[1:]):
        assert prev.parity is not nxt.parity


def test_midweek_start_still_week_one():
    # Семестр починається в середу — перший тиждень однаково №1 ODD.
    sem = _semester(date(2025, 9, 3), date(2025, 12, 28))
    wk = cal.week_for_date(sem, date(2025, 9, 3))
    assert wk.number == 1 and wk.parity is Parity.ODD
    # Понеділок наступного тижня — вже тиждень 2.
    assert cal.week_for_date(sem, date(2025, 9, 8)).number == 2
