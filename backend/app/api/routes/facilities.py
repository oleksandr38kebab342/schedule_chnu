from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import Building, PairTime, Room, RoomAlias, normalize_room_code
from app.schemas.reference import (
    BuildingCreate,
    BuildingRead,
    PairTimeCreate,
    PairTimeRead,
    PairTimeUpdate,
    RoomCreate,
    RoomRead,
)

router = APIRouter(tags=["facilities"])
room_manage = require_permission(permissions.ROOM_MANAGE)


# ---------- Buildings ----------
@router.get("/buildings", response_model=list[BuildingRead])
def list_buildings(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[Building]:
    return list(db.scalars(select(Building).order_by(Building.code)))


@router.post("/buildings", response_model=BuildingRead, status_code=status.HTTP_201_CREATED)
def create_building(
    payload: BuildingCreate, db: Session = Depends(get_db), _=Depends(room_manage)
) -> Building:
    if db.scalar(select(Building).where(Building.code == payload.code)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Корпус {payload.code} вже існує"
        )
    building = Building(**payload.model_dump())
    db.add(building)
    db.commit()
    db.refresh(building)
    return building


# ---------- Rooms ----------
def _to_room_read(room: Room) -> RoomRead:
    return RoomRead(
        id=room.id,
        building_id=room.building_id,
        number=room.number,
        normalized=room.normalized,
        capacity=room.capacity,
        room_type=room.room_type,
        floor=room.floor,
        is_active=room.is_active,
        aliases=[a.alias for a in room.aliases],
    )


@router.get("/rooms", response_model=list[RoomRead])
def list_rooms(
    building_id: int | None = Query(default=None),
    search: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
) -> list[RoomRead]:
    stmt = select(Room)
    if building_id is not None:
        stmt = stmt.where(Room.building_id == building_id)
    rooms = list(db.scalars(stmt))

    if search:
        # Пошук за нормалізованим ключем: «А.203А», «а203а», «А-203А» знайдуть ту саму.
        needle = normalize_room_code(search)
        matched: list[Room] = []
        for room in rooms:
            keys = {room.normalized} | {a.normalized for a in room.aliases}
            if any(needle in key for key in keys):
                matched.append(room)
        rooms = matched

    return [_to_room_read(r) for r in rooms]


@router.post("/rooms", response_model=RoomRead, status_code=status.HTTP_201_CREATED)
def create_room(payload: RoomCreate, db: Session = Depends(get_db), _=Depends(room_manage)) -> RoomRead:
    if db.get(Building, payload.building_id) is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=f"Корпус {payload.building_id} не існує",
        )
    normalized = normalize_room_code(payload.number)
    if db.scalar(
        select(Room).where(Room.building_id == payload.building_id, Room.normalized == normalized)
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Аудиторія {payload.number} у цьому корпусі вже існує",
        )
    room = Room(
        building_id=payload.building_id,
        number=payload.number,
        normalized=normalized,
        capacity=payload.capacity,
        room_type=payload.room_type,
        floor=payload.floor,
    )
    room.aliases = [
        RoomAlias(alias=a, normalized=normalize_room_code(a)) for a in payload.aliases
    ]
    db.add(room)
    db.commit()
    db.refresh(room)
    return _to_room_read(room)


@router.delete("/rooms/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_room(room_id: int, db: Session = Depends(get_db), _=Depends(room_manage)) -> None:
    room = db.get(Room, room_id)
    if room is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Аудиторію не знайдено")
    db.delete(room)
    db.commit()


# ---------- Pair times ----------
@router.get("/times", response_model=list[PairTimeRead])
def list_times(db: Session = Depends(get_db), _=Depends(get_current_user)) -> list[PairTime]:
    return list(db.scalars(select(PairTime).order_by(PairTime.number)))


@router.post("/times", response_model=PairTimeRead, status_code=status.HTTP_201_CREATED)
def create_time(payload: PairTimeCreate, db: Session = Depends(get_db), _=Depends(room_manage)) -> PairTime:
    if payload.ends_at <= payload.starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Час завершення пари має бути пізнішим за початок",
        )
    if db.scalar(select(PairTime).where(PairTime.number == payload.number)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=f"Пара #{payload.number} вже існує"
        )
    pair = PairTime(**payload.model_dump())
    db.add(pair)
    db.commit()
    db.refresh(pair)
    return pair


@router.patch("/times/{time_id}", response_model=PairTimeRead)
def update_time(
    time_id: int, payload: PairTimeUpdate, db: Session = Depends(get_db), _=Depends(room_manage)
) -> PairTime:
    pair = db.get(PairTime, time_id)
    if pair is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Пару не знайдено")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(pair, field, value)
    if pair.ends_at <= pair.starts_at:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Час завершення пари має бути пізнішим за початок",
        )
    db.commit()
    db.refresh(pair)
    return pair
