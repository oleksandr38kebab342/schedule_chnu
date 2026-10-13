import enum
from datetime import date

from sqlalchemy import Date, Enum, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Parity(str, enum.Enum):
    ODD = "ODD"
    EVEN = "EVEN"
    BOTH = "BOTH"


class ExceptionKind(str, enum.Enum):
    HOLIDAY = "HOLIDAY"        # свято / вихідний — занять немає
    VACATION = "VACATION"      # канікули
    WORKING_DAY = "WORKING_DAY"  # робоча субота тощо
    REMOTE = "REMOTE"          # дистанційний день


class AcademicYear(Base, TimestampMixin):
    __tablename__ = "academic_years"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)

    semesters: Mapped[list["Semester"]] = relationship(
        back_populates="academic_year", cascade="all, delete-orphan"
    )


class Semester(Base, TimestampMixin):
    __tablename__ = "semesters"
    __table_args__ = (UniqueConstraint("academic_year_id", "ordinal", name="uq_semester_ordinal"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    academic_year_id: Mapped[int] = mapped_column(
        ForeignKey("academic_years.id", ondelete="CASCADE"), nullable=False, index=True
    )
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 або 2
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date] = mapped_column(Date, nullable=False)
    # Парність першого навчального тижня семестру (зазвичай ODD).
    first_week_parity: Mapped[Parity] = mapped_column(
        Enum(Parity, name="parity"), default=Parity.ODD, nullable=False
    )

    academic_year: Mapped[AcademicYear] = relationship(back_populates="semesters")
    weeks: Mapped[list["AcademicWeek"]] = relationship(
        back_populates="semester", cascade="all, delete-orphan"
    )


class AcademicWeek(Base):
    """Навчальний тиждень семестру. Нумерація завжди від 1 для кожного семестру."""

    __tablename__ = "academic_weeks"
    __table_args__ = (UniqueConstraint("semester_id", "number", name="uq_week_number"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    number: Mapped[int] = mapped_column(Integer, nullable=False)
    parity: Mapped[Parity] = mapped_column(Enum(Parity, name="parity"), nullable=False)
    starts_on: Mapped[date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[date] = mapped_column(Date, nullable=False)

    semester: Mapped[Semester] = relationship(back_populates="weeks")


class CalendarException(Base):
    __tablename__ = "calendar_exceptions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    semester_id: Mapped[int] = mapped_column(
        ForeignKey("semesters.id", ondelete="CASCADE"), nullable=False, index=True
    )
    kind: Mapped[ExceptionKind] = mapped_column(
        Enum(ExceptionKind, name="exception_kind"), nullable=False
    )
    date_from: Mapped[date] = mapped_column(Date, nullable=False)
    date_to: Mapped[date] = mapped_column(Date, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255))
