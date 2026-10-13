import re

from sqlalchemy import Boolean, ForeignKey, Integer, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

_NORMALIZE_RE = re.compile(r"[\s.\-_/]+")


def normalize_room_code(value: str) -> str:
    """А.203А / А203А / А-203А -> а203а. «А.203Б» лишається окремим кодом."""
    return _NORMALIZE_RE.sub("", value).strip().lower()


class Building(Base, TimestampMixin):
    __tablename__ = "buildings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    address: Mapped[str | None] = mapped_column(String(255))

    rooms: Mapped[list["Room"]] = relationship(
        back_populates="building", cascade="all, delete-orphan"
    )


class Room(Base, TimestampMixin):
    __tablename__ = "rooms"
    __table_args__ = (UniqueConstraint("building_id", "number", name="uq_room_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    building_id: Mapped[int] = mapped_column(
        ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[str] = mapped_column(String(64), nullable=False)
    # Нормалізований ключ для пошуку; унікальний у межах корпусу.
    normalized: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    capacity: Mapped[int | None] = mapped_column(Integer)
    room_type: Mapped[str | None] = mapped_column(String(64))
    floor: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    building: Mapped[Building] = relationship(back_populates="rooms")
    aliases: Mapped[list["RoomAlias"]] = relationship(
        back_populates="room", cascade="all, delete-orphan", lazy="selectin"
    )


class RoomAlias(Base):
    """Альтернативні написання номера аудиторії, що вказують на ту саму кімнату."""

    __tablename__ = "room_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    alias: Mapped[str] = mapped_column(String(64), nullable=False)
    normalized: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    room: Mapped[Room] = relationship(back_populates="aliases")


class PairTime(Base):
    """Довідник пар (номер + час). Час може змінюватись адміністратором."""

    __tablename__ = "times"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[int] = mapped_column(Integer, unique=True, nullable=False, index=True)
    starts_at: Mapped["object"] = mapped_column(Time, nullable=False)
    ends_at: Mapped["object"] = mapped_column(Time, nullable=False)
    label: Mapped[str | None] = mapped_column(String(64))
