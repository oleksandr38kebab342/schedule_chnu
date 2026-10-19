from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import (
    ExceptionAction,
    Group,
    PairTime,
    Room,
    ScheduleConflict,
    ScheduleConflictOverride,
    ScheduleEntry,
    ScheduleException,
    ScheduleGroup,
    ScheduleRoom,
    ScheduleStream,
    ScheduleSubgroup,
    ScheduleTeacher,
    Semester,
    Subject,
    Teacher,
    User,
)
from app.schemas.schedule import (
    ConflictRead,
    ScheduleEntryCreate,
    ScheduleEntryCreateResult,
    ScheduleEntryRead,
    ScheduleEntryUpdate,
    ScheduleExceptionCreate,
    ScheduleExceptionRead,
)
from app.services import audit, cache
from app.services.conflicts import Conflict, detect_conflicts

router = APIRouter(prefix="/schedule", tags=["schedule"])
create_perm = require_permission(permissions.SCHEDULE_CREATE)
edit_perm = require_permission(permissions.SCHEDULE_EDIT)
delete_perm = require_permission(permissions.SCHEDULE_DELETE)

# Яке право потрібне для конкретного виду точкової зміни заняття.
_EXCEPTION_PERMISSION = {
    ExceptionAction.ADD: permissions.SCHEDULE_CREATE,
    ExceptionAction.MOVE: permissions.SCHEDULE_MOVE,
    ExceptionAction.CANCEL: permissions.SCHEDULE_CANCEL,
    ExceptionAction.REPLACE: permissions.SCHEDULE_EDIT,
}


def _to_read(entry: ScheduleEntry) -> ScheduleEntryRead:
    return ScheduleEntryRead(
        id=entry.id,
        semester_id=entry.semester_id,
        subject_id=entry.subject_id,
        lesson_type_id=entry.lesson_type_id,
        pair_time_id=entry.pair_time_id,
        day_of_week=entry.day_of_week,
        week_parity=entry.week_parity,
        note=entry.note,
        teacher_ids=[l.teacher_id for l in entry.teachers],
        room_ids=[l.room_id for l in entry.rooms],
        group_ids=[l.group_id for l in entry.groups],
        subgroup_ids=[l.subgroup_id for l in entry.subgroups],
        stream_ids=[l.stream_id for l in entry.streams],
    )


def _conflict_read(c: Conflict) -> ConflictRead:
    return ConflictRead(
        kind=c.kind,
        severity=c.severity,
        resource_id=c.resource_id,
        other_entry_id=c.other_entry_id,
        details=c.details,
    )


def _invalidation_pairs(entry: ScheduleEntry):
    for link in entry.groups:
        yield ("group", link.group_id)
    for link in entry.teachers:
        yield ("teacher", link.teacher_id)
    for link in entry.rooms:
        yield ("room", link.room_id)


def _validate_refs(db: Session, payload: ScheduleEntryCreate) -> None:
    checks = [
        (Semester, payload.semester_id, "Семестр"),
        (Subject, payload.subject_id, "Дисципліна"),
        (PairTime, payload.pair_time_id, "Пара"),
    ]
    for model, obj_id, label in checks:
        if db.get(model, obj_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{label} {obj_id} не існує",
            )


def _record_conflicts(
    db: Session,
    entry: ScheduleEntry,
    conflicts: list[Conflict],
    reason: str,
    user: User,
) -> None:
    """Фіксує конфлікти та причину свідомого збереження (ТЗ, розділ 42)."""
    for c in conflicts:
        record = ScheduleConflict(
            entry_id=entry.id,
            other_entry_id=c.other_entry_id,
            kind=c.kind,
            severity=c.severity,
            resource_id=c.resource_id,
            details=c.details,
        )
        db.add(record)
        db.flush()
        if c.severity.value == "ERROR":
            db.add(
                ScheduleConflictOverride(
                    conflict_id=record.id, reason=reason, created_by=user.id
                )
            )
    audit.record(
        db,
        user_id=user.id,
        action="schedule.override_conflict",
        entity_type="schedule_entry",
        entity_id=entry.id,
        new_value={"conflicts": len(conflicts)},
        reason=reason,
    )


def _assign_links(db: Session, entry: ScheduleEntry, payload: ScheduleEntryCreate) -> None:
    """Перезаписує звʼязки заняття (дублікати в запиті ігноруються).

    Старі звʼязки прибираємо окремим flush: інакше SQLAlchemy може вставити
    новий рядок раніше, ніж видалить попередній, і впертися в UNIQUE-обмеження
    при редагуванні заняття на ті самі групи.
    """
    if entry.id is not None:
        for collection in (
            entry.teachers,
            entry.rooms,
            entry.groups,
            entry.subgroups,
            entry.streams,
        ):
            collection.clear()
        db.flush()

    entry.teachers = [ScheduleTeacher(teacher_id=i) for i in dict.fromkeys(payload.teacher_ids)]
    entry.rooms = [ScheduleRoom(room_id=i) for i in dict.fromkeys(payload.room_ids)]
    entry.groups = [ScheduleGroup(group_id=i) for i in dict.fromkeys(payload.group_ids)]
    entry.subgroups = [ScheduleSubgroup(subgroup_id=i) for i in dict.fromkeys(payload.subgroup_ids)]
    entry.streams = [ScheduleStream(stream_id=i) for i in dict.fromkeys(payload.stream_ids)]


@router.post("", response_model=ScheduleEntryCreateResult)
def create_entry(
    payload: ScheduleEntryCreate,
    db: Session = Depends(get_db),
    user: User = Depends(create_perm),
) -> ScheduleEntryCreateResult:
    _validate_refs(db, payload)

    entry = ScheduleEntry(
        semester_id=payload.semester_id,
        subject_id=payload.subject_id,
        lesson_type_id=payload.lesson_type_id,
        pair_time_id=payload.pair_time_id,
        day_of_week=payload.day_of_week,
        week_parity=payload.week_parity,
        note=payload.note,
        created_by=user.id,
        updated_by=user.id,
    )
    _assign_links(db, entry, payload)

    # Додаємо в сесію без commit, щоб детектор бачив звʼязки, але не фіксуємо
    # до перевірки конфліктів.
    db.add(entry)
    db.flush()

    conflicts = detect_conflicts(db, entry)
    blocking = [c for c in conflicts if c.severity.value == "ERROR"]

    if blocking and not payload.override_reason:
        # Нічого не зберігаємо: повертаємо конфлікти, рішення за користувачем.
        db.rollback()
        return ScheduleEntryCreateResult(
            entry=None, conflicts=[_conflict_read(c) for c in conflicts], saved=False
        )

    overridden = False
    if blocking and payload.override_reason:
        if permissions.SCHEDULE_OVERRIDE_CONFLICT not in user.permission_codes:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Немає права зберігати попри конфлікт (schedule.override_conflict)",
            )
        overridden = True
        _record_conflicts(db, entry, conflicts, payload.override_reason, user)

    audit.record(
        db,
        user_id=user.id,
        action="schedule.create",
        entity_type="schedule_entry",
        entity_id=entry.id,
    )
    db.commit()
    db.refresh(entry)
    cache.invalidate(_invalidation_pairs(entry))

    return ScheduleEntryCreateResult(
        entry=_to_read(entry),
        conflicts=[_conflict_read(c) for c in conflicts],
        saved=True,
        overridden=overridden,
    )


@router.get("/group/{group_id}", response_model=list[ScheduleEntryRead])
def schedule_for_group(
    group_id: int,
    semester_id: int = Query(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[ScheduleEntryRead]:
    if db.get(Group, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Групу не знайдено")

    cached = cache.get_cached("group", f"{group_id}:{semester_id}")
    if cached is not None:
        return [ScheduleEntryRead(**item) for item in cached]

    entries = db.scalars(
        select(ScheduleEntry)
        .join(ScheduleGroup, ScheduleGroup.entry_id == ScheduleEntry.id)
        .where(ScheduleGroup.group_id == group_id, ScheduleEntry.semester_id == semester_id)
        .order_by(ScheduleEntry.day_of_week, ScheduleEntry.pair_time_id)
    ).all()
    result = [_to_read(e) for e in entries]
    cache.set_cached("group", f"{group_id}:{semester_id}", [r.model_dump() for r in result])
    return result


@router.get("/teacher/{teacher_id}", response_model=list[ScheduleEntryRead])
def schedule_for_teacher(
    teacher_id: int,
    semester_id: int = Query(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[ScheduleEntryRead]:
    if db.get(Teacher, teacher_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Викладача не знайдено")
    entries = db.scalars(
        select(ScheduleEntry)
        .join(ScheduleTeacher, ScheduleTeacher.entry_id == ScheduleEntry.id)
        .where(ScheduleTeacher.teacher_id == teacher_id, ScheduleEntry.semester_id == semester_id)
        .order_by(ScheduleEntry.day_of_week, ScheduleEntry.pair_time_id)
    ).all()
    return [_to_read(e) for e in entries]


@router.get("/room/{room_id}", response_model=list[ScheduleEntryRead])
def schedule_for_room(
    room_id: int,
    semester_id: int = Query(...),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[ScheduleEntryRead]:
    if db.get(Room, room_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аудиторію не знайдено")
    entries = db.scalars(
        select(ScheduleEntry)
        .join(ScheduleRoom, ScheduleRoom.entry_id == ScheduleEntry.id)
        .where(ScheduleRoom.room_id == room_id, ScheduleEntry.semester_id == semester_id)
        .order_by(ScheduleEntry.day_of_week, ScheduleEntry.pair_time_id)
    ).all()
    return [_to_read(e) for e in entries]


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_entry(
    entry_id: int, db: Session = Depends(get_db), user: User = Depends(delete_perm)
) -> None:
    entry = db.get(ScheduleEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заняття не знайдено")
    pairs = list(_invalidation_pairs(entry))
    audit.record(
        db,
        user_id=user.id,
        action="schedule.delete",
        entity_type="schedule_entry",
        entity_id=entry_id,
    )
    db.delete(entry)
    db.commit()
    cache.invalidate(pairs)


@router.put("/{entry_id}", response_model=ScheduleEntryCreateResult)
def update_entry(
    entry_id: int,
    payload: ScheduleEntryUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(edit_perm),
) -> ScheduleEntryCreateResult:
    """Повна заміна заняття з тією самою перевіркою конфліктів, що й створення."""
    entry = db.get(ScheduleEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заняття не знайдено")
    _validate_refs(db, payload)

    before = _to_read(entry)
    stale_pairs = list(_invalidation_pairs(entry))

    entry.semester_id = payload.semester_id
    entry.subject_id = payload.subject_id
    entry.lesson_type_id = payload.lesson_type_id
    entry.pair_time_id = payload.pair_time_id
    entry.day_of_week = payload.day_of_week
    entry.week_parity = payload.week_parity
    entry.note = payload.note
    entry.updated_by = user.id
    _assign_links(db, entry, payload)
    db.flush()

    conflicts = detect_conflicts(db, entry)
    blocking = [c for c in conflicts if c.severity.value == "ERROR"]

    if blocking and not payload.override_reason:
        # Правку не застосовуємо: заняття лишається таким, яким було.
        db.rollback()
        return ScheduleEntryCreateResult(
            entry=None, conflicts=[_conflict_read(c) for c in conflicts], saved=False
        )

    overridden = False
    if blocking and payload.override_reason:
        if permissions.SCHEDULE_OVERRIDE_CONFLICT not in user.permission_codes:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Немає права зберігати попри конфлікт (schedule.override_conflict)",
            )
        overridden = True
        _record_conflicts(db, entry, conflicts, payload.override_reason, user)

    audit.record(
        db,
        user_id=user.id,
        action="schedule.edit",
        entity_type="schedule_entry",
        entity_id=entry.id,
        old_value=before.model_dump(mode="json"),
        new_value=payload.model_dump(mode="json", exclude={"override_reason"}),
        reason=payload.override_reason,
    )
    db.commit()
    db.refresh(entry)
    cache.invalidate(stale_pairs)
    cache.invalidate(_invalidation_pairs(entry))

    return ScheduleEntryCreateResult(
        entry=_to_read(entry),
        conflicts=[_conflict_read(c) for c in conflicts],
        saved=True,
        overridden=overridden,
    )


@router.get("/{entry_id}", response_model=ScheduleEntryRead)
def get_entry(
    entry_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> ScheduleEntryRead:
    entry = db.get(ScheduleEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заняття не знайдено")
    return _to_read(entry)


@router.get("/{entry_id}/exceptions", response_model=list[ScheduleExceptionRead])
def list_exceptions(
    entry_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> list[ScheduleException]:
    if db.get(ScheduleEntry, entry_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заняття не знайдено")
    return list(
        db.scalars(
            select(ScheduleException)
            .where(ScheduleException.entry_id == entry_id)
            .order_by(ScheduleException.on_date)
        )
    )


@router.post(
    "/{entry_id}/exceptions",
    response_model=ScheduleExceptionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_exception(
    entry_id: int,
    payload: ScheduleExceptionCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> ScheduleException:
    """Скасування, перенесення, заміна або додаткове заняття на конкретну дату.

    Право залежить від дії: скасування — schedule.cancel, перенесення —
    schedule.move, заміна — schedule.edit, додаткове заняття — schedule.create.
    """
    entry = db.get(ScheduleEntry, entry_id)
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Заняття не знайдено")

    needed = _EXCEPTION_PERMISSION[payload.action]
    if needed not in user.permission_codes:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=f"Недостатньо прав: потрібне {needed}"
        )

    for model, obj_id, label in (
        (PairTime, payload.new_pair_time_id, "Пара"),
        (Room, payload.new_room_id, "Аудиторія"),
        (Teacher, payload.new_teacher_id, "Викладач"),
    ):
        if obj_id is not None and db.get(model, obj_id) is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=f"{label} {obj_id} не існує",
            )

    exception = ScheduleException(
        entry_id=entry_id,
        action=payload.action,
        on_date=payload.on_date,
        new_date=payload.new_date,
        new_pair_time_id=payload.new_pair_time_id,
        new_room_id=payload.new_room_id,
        new_teacher_id=payload.new_teacher_id,
        reason=payload.reason,
        created_by=user.id,
    )
    db.add(exception)
    audit.record(
        db,
        user_id=user.id,
        action=f"schedule.exception.{payload.action.value.lower()}",
        entity_type="schedule_entry",
        entity_id=entry_id,
        new_value=payload.model_dump(mode="json"),
        reason=payload.reason,
    )
    db.commit()
    db.refresh(exception)
    cache.invalidate(_invalidation_pairs(entry))
    return exception


@router.delete("/exceptions/{exception_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exception(
    exception_id: int, db: Session = Depends(get_db), user: User = Depends(edit_perm)
) -> None:
    """Скасовує точкову зміну — заняття повертається до базового шаблону."""
    exception = db.get(ScheduleException, exception_id)
    if exception is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Зміну не знайдено")
    entry = db.get(ScheduleEntry, exception.entry_id)
    pairs = list(_invalidation_pairs(entry)) if entry else []
    audit.record(
        db,
        user_id=user.id,
        action="schedule.exception.delete",
        entity_type="schedule_entry",
        entity_id=exception.entry_id,
        old_value={"action": exception.action.value, "on_date": exception.on_date.isoformat()},
    )
    db.delete(exception)
    db.commit()
    cache.invalidate(pairs)
