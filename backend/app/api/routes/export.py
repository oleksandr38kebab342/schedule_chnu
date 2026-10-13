from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import (
    Group,
    LessonType,
    PairTime,
    Room,
    ScheduleEntry,
    ScheduleGroup,
    Subject,
    Teacher,
)
from app.services import audit
from app.services.excel_export import Grid, Lesson, PairSlot, build_grid, generate_workbook

router = APIRouter(prefix="/export", tags=["export"])
export_perm = require_permission(permissions.SCHEDULE_EXPORT)


class ExportRequest(BaseModel):
    semester_id: int
    group_ids: list[int] = Field(min_length=1)


def _lesson_text(
    db: Session,
    entry: ScheduleEntry,
    subjects: dict[int, Subject],
    types: dict[int, LessonType],
    teachers: dict[int, Teacher],
    rooms: dict[int, Room],
) -> str:
    subject = subjects.get(entry.subject_id)
    ltype = types.get(entry.lesson_type_id)
    lines = [subject.short_name or subject.name if subject else f"#{entry.subject_id}"]
    if ltype:
        lines[0] += f" ({ltype.short_name or ltype.code})"
    teacher_names = [
        teachers[l.teacher_id].short_name or teachers[l.teacher_id].full_name
        for l in entry.teachers
        if l.teacher_id in teachers
    ]
    if teacher_names:
        lines.append(", ".join(teacher_names))
    room_numbers = [rooms[l.room_id].number for l in entry.rooms if l.room_id in rooms]
    if room_numbers:
        lines.append(", ".join(room_numbers))
    return "\n".join(lines)


@router.post("")
def export_groups(
    payload: ExportRequest, db: Session = Depends(get_db), user=Depends(export_perm)
) -> Response:
    # selected = existing ∩ requested, щоб не експортувати неіснуючі групи.
    requested = list(dict.fromkeys(payload.group_ids))
    groups = {
        g.id: g for g in db.scalars(select(Group).where(Group.id.in_(requested)))
    }
    selected = [gid for gid in requested if gid in groups]
    if not selected:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Жодної з указаних груп не існує",
        )

    pair_rows = list(db.scalars(select(PairTime).order_by(PairTime.number)))
    pair_slots = [PairSlot(number=p.number, starts_at=p.starts_at, ends_at=p.ends_at) for p in pair_rows]
    pair_by_id = {p.id: p.number for p in pair_rows}

    subjects = {s.id: s for s in db.scalars(select(Subject))}
    types = {t.id: t for t in db.scalars(select(LessonType))}
    teachers = {t.id: t for t in db.scalars(select(Teacher))}
    rooms = {r.id: r for r in db.scalars(select(Room))}

    sheets: list[tuple[str, Grid]] = []
    total_lessons = 0
    for gid in selected:
        entries = db.scalars(
            select(ScheduleEntry)
            .join(ScheduleGroup, ScheduleGroup.entry_id == ScheduleEntry.id)
            .where(ScheduleGroup.group_id == gid, ScheduleEntry.semester_id == payload.semester_id)
        ).all()
        lessons = [
            Lesson(
                day_of_week=e.day_of_week,
                pair_number=pair_by_id.get(e.pair_time_id, 0),
                parity=e.week_parity,
                text=_lesson_text(db, e, subjects, types, teachers, rooms),
            )
            for e in entries
        ]
        total_lessons += len(lessons)
        sheets.append((groups[gid].name, build_grid(lessons, pair_slots)))

    content = generate_workbook(sheets)

    audit.record(
        db,
        user_id=user.id,
        action="schedule.export",
        entity_type="schedule",
        new_value={"groups": selected, "lessons": total_lessons},
    )
    db.commit()

    filename = f"rozklad_{payload.semester_id}.xlsx"
    return Response(
        content=content,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
