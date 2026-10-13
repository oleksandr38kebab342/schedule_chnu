"""Генерація навчальних тижнів семестру та обчислення парності.

Правила ТЗ (розділ 103):
- номер тижня рахується від semester.start_date, а не від ISO-тижня року;
- кожен семестр починає власну нумерацію з 1;
- парність чергується, старт — semester.first_week_parity (зазвичай ODD).
"""

from dataclasses import dataclass
from datetime import date, timedelta

from app.models import AcademicWeek, Parity, Semester


def _flip(parity: Parity) -> Parity:
    return Parity.EVEN if parity is Parity.ODD else Parity.ODD


def _week_monday(day: date) -> date:
    return day - timedelta(days=day.weekday())


@dataclass(frozen=True)
class WeekPlan:
    number: int
    parity: Parity
    starts_on: date
    ends_on: date


def plan_weeks(semester: Semester) -> list[WeekPlan]:
    """Будує перелік тижнів від start_date до end_date включно.

    Тиждень 1 — той, що містить start_date; межі тижня вирівняно по Пн-Нд,
    але перший тиждень не виходить раніше за start_date.
    """
    if semester.end_date < semester.start_date:
        raise ValueError("Дата завершення семестру раніша за дату початку")

    plans: list[WeekPlan] = []
    parity = semester.first_week_parity
    number = 1
    cursor = _week_monday(semester.start_date)

    while cursor <= semester.end_date:
        starts = max(cursor, semester.start_date)
        ends = min(cursor + timedelta(days=6), semester.end_date)
        plans.append(WeekPlan(number=number, parity=parity, starts_on=starts, ends_on=ends))
        number += 1
        parity = _flip(parity)
        cursor += timedelta(days=7)

    return plans


def generate_weeks(semester: Semester) -> list[AcademicWeek]:
    """Повертає ORM-обʼєкти тижнів (ще не додані в сесію)."""
    return [
        AcademicWeek(
            semester_id=semester.id,
            number=p.number,
            parity=p.parity,
            starts_on=p.starts_on,
            ends_on=p.ends_on,
        )
        for p in plan_weeks(semester)
    ]


def week_for_date(semester: Semester, day: date) -> WeekPlan | None:
    """Який навчальний тиждень припадає на вказану дату (None — поза семестром)."""
    for plan in plan_weeks(semester):
        if plan.starts_on <= day <= plan.ends_on:
            return plan
    return None


def parity_for_date(semester: Semester, day: date) -> Parity | None:
    plan = week_for_date(semester, day)
    return plan.parity if plan else None
