import re

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

_NATURAL_KEY_RE = re.compile(r"(\d+|\D+)")


def natural_key(value: str) -> list:
    """Ключ природного сортування: КН-1, КН-2, КН-10 (а не КН-1, КН-10, КН-2)."""
    parts = _NATURAL_KEY_RE.findall(value)
    return [(1, int(p)) if p.isdigit() else (0, p.lower()) for p in parts]


class Group(Base, TimestampMixin):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    course: Mapped[int | None] = mapped_column(Integer)
    students_count: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    subgroups: Mapped[list["Subgroup"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class Subgroup(Base):
    """Підгрупа (121 -> 121-1 / 121-2). Може мати власного викладача й аудиторію."""

    __tablename__ = "subgroups"
    __table_args__ = (UniqueConstraint("group_id", "name", name="uq_subgroup_name"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(64), nullable=False)

    group: Mapped[Group] = relationship(back_populates="subgroups")


class Stream(Base, TimestampMixin):
    """Потік — іменоване обʼєднання груп для спільних занять."""

    __tablename__ = "streams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    group_links: Mapped[list["StreamGroup"]] = relationship(
        back_populates="stream", cascade="all, delete-orphan", lazy="selectin"
    )


class StreamGroup(Base):
    __tablename__ = "stream_groups"
    __table_args__ = (UniqueConstraint("stream_id", "group_id", name="uq_stream_group"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    stream_id: Mapped[int] = mapped_column(
        ForeignKey("streams.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False, index=True
    )

    stream: Mapped[Stream] = relationship(back_populates="group_links")
    group: Mapped[Group] = relationship(lazy="selectin")


class LessonType(Base):
    __tablename__ = "lesson_types"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(32))


class Subject(Base, TimestampMixin):
    __tablename__ = "subjects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    department_links: Mapped[list["SubjectDepartment"]] = relationship(
        back_populates="subject", cascade="all, delete-orphan", lazy="selectin"
    )


class SubjectDepartment(Base):
    __tablename__ = "subject_departments"
    __table_args__ = (UniqueConstraint("subject_id", "department_id", name="uq_subject_department"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_id: Mapped[int] = mapped_column(
        ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )

    subject: Mapped[Subject] = relationship(back_populates="department_links")
    department: Mapped["object"] = relationship("Department", lazy="selectin")
