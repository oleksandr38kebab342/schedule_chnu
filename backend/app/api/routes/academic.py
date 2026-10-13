from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import (
    Department,
    Group,
    LessonType,
    Stream,
    StreamGroup,
    Subgroup,
    Subject,
    SubjectDepartment,
    natural_key,
)
from app.schemas.reference import (
    GroupCreate,
    GroupRead,
    GroupUpdate,
    LessonTypeCreate,
    LessonTypeRead,
    StreamCreate,
    StreamRead,
    SubgroupCreate,
    SubgroupRead,
    SubjectCreate,
    SubjectRead,
)

router = APIRouter(tags=["academic"])
group_manage = require_permission(permissions.GROUP_MANAGE)
subject_manage = require_permission(permissions.SUBJECT_MANAGE)


def _validate_departments(db: Session, ids: list[int]) -> list[int]:
    ids = list(dict.fromkeys(ids))
    existing = {d for d in db.scalars(select(Department.id).where(Department.id.in_(ids)))}
    missing = set(ids) - existing
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Кафедри не існують: {sorted(missing)}",
        )
    return ids


# ---------- Groups ----------
@router.get("/groups", response_model=list[GroupRead])
def list_groups(
    department_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[Group]:
    stmt = select(Group)
    if department_id is not None:
        stmt = stmt.where(Group.department_id == department_id)
    groups = db.scalars(stmt).all()
    return sorted(groups, key=lambda g: natural_key(g.name))


@router.post("/groups", response_model=GroupRead, status_code=status.HTTP_201_CREATED)
def create_group(payload: GroupCreate, db: Session = Depends(get_db), _=Depends(group_manage)) -> Group:
    if db.get(Department, payload.department_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Кафедра {payload.department_id} не існує",
        )
    if db.scalar(select(Group).where(Group.name == payload.name)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Група {payload.name} вже існує"
        )
    group = Group(**payload.model_dump())
    db.add(group)
    db.commit()
    db.refresh(group)
    return group


@router.patch("/groups/{group_id}", response_model=GroupRead)
def update_group(
    group_id: int, payload: GroupUpdate, db: Session = Depends(get_db), _=Depends(group_manage)
) -> Group:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Групу не знайдено")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete("/groups/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_group(group_id: int, db: Session = Depends(get_db), _=Depends(group_manage)) -> None:
    group = db.get(Group, group_id)
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Групу не знайдено")
    db.delete(group)
    db.commit()


@router.post(
    "/groups/{group_id}/subgroups", response_model=SubgroupRead, status_code=status.HTTP_201_CREATED
)
def add_subgroup(
    group_id: int, payload: SubgroupCreate, db: Session = Depends(get_db), _=Depends(group_manage)
) -> Subgroup:
    if db.get(Group, group_id) is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Групу не знайдено")
    if db.scalar(
        select(Subgroup).where(Subgroup.group_id == group_id, Subgroup.name == payload.name)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Підгрупа з такою назвою вже існує"
        )
    subgroup = Subgroup(group_id=group_id, name=payload.name)
    db.add(subgroup)
    db.commit()
    db.refresh(subgroup)
    return subgroup


@router.get("/groups/{group_id}/subgroups", response_model=list[SubgroupRead])
def list_subgroups(
    group_id: int, db: Session = Depends(get_db), _=Depends(get_current_user)
) -> list[Subgroup]:
    return list(db.scalars(select(Subgroup).where(Subgroup.group_id == group_id)))


# ---------- Streams ----------
@router.get("/streams", response_model=list[StreamRead])
def list_streams(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[StreamRead]:
    streams = db.scalars(select(Stream).order_by(Stream.name)).all()
    return [
        StreamRead(
            id=s.id,
            name=s.name,
            is_active=s.is_active,
            group_ids=[link.group_id for link in s.group_links],
        )
        for s in streams
    ]


@router.post("/streams", response_model=StreamRead, status_code=status.HTTP_201_CREATED)
def create_stream(
    payload: StreamCreate, db: Session = Depends(get_db), _=Depends(group_manage)
) -> StreamRead:
    group_ids = list(dict.fromkeys(payload.group_ids))
    existing = {g for g in db.scalars(select(Group.id).where(Group.id.in_(group_ids)))}
    missing = set(group_ids) - existing
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Групи не існують: {sorted(missing)}",
        )
    stream = Stream(name=payload.name)
    stream.group_links = [StreamGroup(group_id=g) for g in group_ids]
    db.add(stream)
    db.commit()
    db.refresh(stream)
    return StreamRead(
        id=stream.id,
        name=stream.name,
        is_active=stream.is_active,
        group_ids=[link.group_id for link in stream.group_links],
    )


@router.delete("/streams/{stream_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stream(stream_id: int, db: Session = Depends(get_db), _=Depends(group_manage)) -> None:
    stream = db.get(Stream, stream_id)
    if stream is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Потік не знайдено")
    db.delete(stream)
    db.commit()


# ---------- Subjects ----------
@router.get("/subjects", response_model=list[SubjectRead])
def list_subjects(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[Subject]:
    return list(db.scalars(select(Subject).order_by(Subject.name)))


@router.post("/subjects", response_model=SubjectRead, status_code=status.HTTP_201_CREATED)
def create_subject(
    payload: SubjectCreate, db: Session = Depends(get_db), _=Depends(subject_manage)
) -> Subject:
    if db.scalar(select(Subject).where(Subject.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Дисципліна {payload.code} вже існує"
        )
    dept_ids = _validate_departments(db, payload.department_ids)
    subject = Subject(name=payload.name, code=payload.code, short_name=payload.short_name)
    subject.department_links = [SubjectDepartment(department_id=d) for d in dept_ids]
    db.add(subject)
    db.commit()
    db.refresh(subject)
    return subject


@router.delete("/subjects/{subject_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_subject(subject_id: int, db: Session = Depends(get_db), _=Depends(subject_manage)) -> None:
    subject = db.get(Subject, subject_id)
    if subject is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Дисципліну не знайдено")
    db.delete(subject)
    db.commit()


# ---------- Lesson types ----------
@router.get("/lesson-types", response_model=list[LessonTypeRead])
def list_lesson_types(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[LessonType]:
    return list(db.scalars(select(LessonType).order_by(LessonType.code)))


@router.post("/lesson-types", response_model=LessonTypeRead, status_code=status.HTTP_201_CREATED)
def create_lesson_type(
    payload: LessonTypeCreate, db: Session = Depends(get_db), _=Depends(subject_manage)
) -> LessonType:
    if db.scalar(select(LessonType).where(LessonType.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Тип заняття {payload.code} вже існує"
        )
    lesson_type = LessonType(**payload.model_dump())
    db.add(lesson_type)
    db.commit()
    db.refresh(lesson_type)
    return lesson_type
