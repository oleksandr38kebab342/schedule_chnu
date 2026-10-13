import enum
from datetime import date

from sqlalchemy import (
    Date,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.calendar import Parity


class ExceptionAction(str, enum.Enum):
    ADD = "ADD"
    MOVE = "MOVE"
    CANCEL = "CANCEL"
    REPLACE = "REPLACE"


class ConflictKind(str, enum.Enum):
    TEACHER = "TEACHER"
    ROOM = "ROOM"
    GROUP = "GROUP"
    SUBGROUP = "SUBGROUP"


class ConflictSeverity(str, enum.Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class ScheduleEntry(Base, TimestampMixin):
    """Базове заняття розкладу — одна логічна сутність навіть для спільної пари
    кількох груп/викладачів/аудиторій (ТЗ, розділи 20-28)."""

    __tablename__ = "schedule_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    lesson_type_id: Mapped[int] = mapped_column(
        ForeignKey("lesson_types.id", ondelete="RESTRICT"), nullable=False
    )
    pair_time_id: Mapped[int] = mapped_column(
        ForeignKey("times.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 1=Пн ... 7=Нд
    week_parity: Mapped[Parity] = mapped_column(Enum(Parity, name="parity"), nullable=False)
    note: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    teachers: Mapped[list["ScheduleTeacher"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )
    rooms: Mapped[list["ScheduleRoom"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )
    groups: Mapped[list["ScheduleGroup"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )
    subgroups: Mapped[list["ScheduleSubgroup"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )
    streams: Mapped[list["ScheduleStream"]] = relationship(
        back_populates="entry", cascade="all, delete-orphan", lazy="selectin"
    )


class ScheduleTeacher(Base):
    __tablename__ = "schedule_teachers"
    __table_args__ = (UniqueConstraint("entry_id", "teacher_id", name="uq_schedule_teacher"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry: Mapped[ScheduleEntry] = relationship(back_populates="teachers")


class ScheduleRoom(Base):
    __tablename__ = "schedule_rooms"
    __table_args__ = (UniqueConstraint("entry_id", "room_id", name="uq_schedule_room"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    room_id: Mapped[int] = mapped_column(
        ForeignKey("rooms.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry: Mapped[ScheduleEntry] = relationship(back_populates="rooms")


class ScheduleGroup(Base):
    __tablename__ = "schedule_groups"
    __table_args__ = (UniqueConstraint("entry_id", "group_id", name="uq_schedule_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry: Mapped[ScheduleEntry] = relationship(back_populates="groups")


class ScheduleSubgroup(Base):
    __tablename__ = "schedule_subgroups"
    __table_args__ = (UniqueConstraint("entry_id", "subgroup_id", name="uq_schedule_subgroup"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subgroup_id: Mapped[int] = mapped_column(
        ForeignKey("subgroups.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry: Mapped[ScheduleEntry] = relationship(back_populates="subgroups")


class ScheduleStream(Base):
    __tablename__ = "schedule_streams"
    __table_args__ = (UniqueConstraint("entry_id", "stream_id", name="uq_schedule_stream"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    stream_id: Mapped[int] = mapped_column(
        ForeignKey("streams.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    entry: Mapped[ScheduleEntry] = relationship(back_populates="streams")


class ScheduleException(Base, TimestampMixin):
    """Точкова зміна заняття на конкретну дату без зміни базового шаблону."""

    __tablename__ = "schedule_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    action: Mapped[ExceptionAction] = mapped_column(
        Enum(ExceptionAction, name="exception_action"), nullable=False
    )
    on_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    new_pair_time_id: Mapped[int | None] = mapped_column(ForeignKey("times.id", ondelete="SET NULL"))
    new_room_id: Mapped[int | None] = mapped_column(ForeignKey("rooms.id", ondelete="SET NULL"))
    reason: Mapped[str | None] = mapped_column(String(255))
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))


class ScheduleConflict(Base, TimestampMixin):
    """Зафіксований конфлікт між двома заняттями за спільним ресурсом."""

    __tablename__ = "schedule_conflicts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    other_entry_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ConflictKind] = mapped_column(
        Enum(ConflictKind, name="conflict_kind"), nullable=False
    )
    severity: Mapped[ConflictSeverity] = mapped_column(
        Enum(ConflictSeverity, name="conflict_severity"), nullable=False
    )
    resource_id: Mapped[int] = mapped_column(Integer, nullable=False)
    details: Mapped[str | None] = mapped_column(Text)

    override: Mapped["ScheduleConflictOverride | None"] = relationship(
        back_populates="conflict", cascade="all, delete-orphan", uselist=False
    )


class ScheduleConflictOverride(Base, TimestampMixin):
    """Свідоме збереження попри конфлікт з обов'язковою причиною."""

    __tablename__ = "schedule_conflict_overrides"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    conflict_id: Mapped[int] = mapped_column(
        ForeignKey("schedule_conflicts.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    reason: Mapped[str] = mapped_column(String(500), nullable=False)
    created_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))

    conflict: Mapped[ScheduleConflict] = relationship(back_populates="override")
