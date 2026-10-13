from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Faculty(Base, TimestampMixin):
    __tablename__ = "faculties"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    departments: Mapped[list["Department"]] = relationship(
        back_populates="faculty", cascade="all, delete-orphan"
    )


class Department(Base, TimestampMixin):
    """Кафедра. parent_id дозволяє вкладені підрозділи (ТЗ, розділ 5)."""

    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    faculty_id: Mapped[int] = mapped_column(
        ForeignKey("faculties.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parent_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id", ondelete="SET NULL"))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    short_name: Mapped[str | None] = mapped_column(String(64))
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    faculty: Mapped[Faculty] = relationship(back_populates="departments")


class Teacher(Base, TimestampMixin):
    """Викладач. Одна особа може працювати на кількох кафедрах (сумісництво),
    тому звʼязок з кафедрою винесено в teacher_departments (ТЗ, розділ 9)."""

    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    middle_name: Mapped[str | None] = mapped_column(String(128))
    short_name: Mapped[str | None] = mapped_column(String(128))
    degree: Mapped[str | None] = mapped_column(String(128))
    position: Mapped[str | None] = mapped_column(String(128))
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    department_links: Mapped[list["TeacherDepartment"]] = relationship(
        back_populates="teacher", cascade="all, delete-orphan", lazy="selectin"
    )

    @property
    def full_name(self) -> str:
        parts = [self.last_name, self.first_name, self.middle_name or ""]
        return " ".join(p for p in parts if p).strip()


class TeacherDepartment(Base):
    """Прив'язка викладача до кафедри з періодом дії та ознакою основної."""

    __tablename__ = "teacher_departments"
    __table_args__ = (
        UniqueConstraint("teacher_id", "department_id", name="uq_teacher_department"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    teacher_id: Mapped[int] = mapped_column(
        ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    department_id: Mapped[int] = mapped_column(
        ForeignKey("departments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    is_primary: Mapped[bool] = mapped_column(default=False, nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_to: Mapped[date | None] = mapped_column(Date)

    teacher: Mapped[Teacher] = relationship(back_populates="department_links")
    department: Mapped[Department] = relationship(lazy="selectin")
