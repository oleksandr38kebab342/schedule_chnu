"""Виявлення конфліктів розкладу (ТЗ, розділ 104).

Два заняття конфліктують, якщо збігаються семестр, день тижня, номер пари,
перетинаються за парністю тижнів і ділять спільний ресурс (викладача,
аудиторію, групу або підгрупу).

Таблиця парності:
    ODD  + ODD   -> конфлікт
    EVEN + EVEN  -> конфлікт
    BOTH + будь-що -> конфлікт
    ODD  + EVEN  -> НЕ конфлікт (різні тижні)
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    ConflictKind,
    ConflictSeverity,
    Parity,
    ScheduleEntry,
)


def parity_overlaps(a: Parity, b: Parity) -> bool:
    if a is Parity.BOTH or b is Parity.BOTH:
        return True
    return a is b


@dataclass(frozen=True)
class Conflict:
    other_entry_id: int
    kind: ConflictKind
    severity: ConflictSeverity
    resource_id: int
    details: str


def _resource_ids(entry: ScheduleEntry, kind: ConflictKind) -> set[int]:
    if kind is ConflictKind.TEACHER:
        return {link.teacher_id for link in entry.teachers}
    if kind is ConflictKind.ROOM:
        return {link.room_id for link in entry.rooms}
    if kind is ConflictKind.GROUP:
        return {link.group_id for link in entry.groups}
    if kind is ConflictKind.SUBGROUP:
        return {link.subgroup_id for link in entry.subgroups}
    return set()


# Один і той самий викладач/аудиторія у двох парах одночасно — це помилка;
# збіг групи ще може бути свідомим (потік), тому ватага нижча.
_SEVERITY = {
    ConflictKind.TEACHER: ConflictSeverity.ERROR,
    ConflictKind.ROOM: ConflictSeverity.ERROR,
    ConflictKind.GROUP: ConflictSeverity.WARNING,
    ConflictKind.SUBGROUP: ConflictSeverity.WARNING,
}

_LABEL = {
    ConflictKind.TEACHER: "викладач",
    ConflictKind.ROOM: "аудиторія",
    ConflictKind.GROUP: "група",
    ConflictKind.SUBGROUP: "підгрупа",
}


def detect_conflicts(db: Session, entry: ScheduleEntry) -> list[Conflict]:
    """Шукає конфлікти заняття з іншими заняттями того ж часового слоту.

    Групи порівнюються також з їхніми потоками: якщо заняття веде потік, що
    містить групу іншого заняття, це той самий фізичний збіг.
    """
    candidates = db.scalars(
        select(ScheduleEntry).where(
            ScheduleEntry.semester_id == entry.semester_id,
            ScheduleEntry.day_of_week == entry.day_of_week,
            ScheduleEntry.pair_time_id == entry.pair_time_id,
            ScheduleEntry.id != entry.id,
        )
    ).all()

    found: list[Conflict] = []
    for other in candidates:
        if not parity_overlaps(entry.week_parity, other.week_parity):
            continue

        for kind in ConflictKind:
            shared = _resource_ids(entry, kind) & _resource_ids(other, kind)
            for resource_id in sorted(shared):
                found.append(
                    Conflict(
                        other_entry_id=other.id,
                        kind=kind,
                        severity=_SEVERITY[kind],
                        resource_id=resource_id,
                        details=(
                            f"Спільний ресурс ({_LABEL[kind]} #{resource_id}) "
                            f"у день {entry.day_of_week}, пара #{entry.pair_time_id}"
                        ),
                    )
                )
    return found
