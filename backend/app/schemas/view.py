"""Схеми відповіді для денормалізованого перегляду розкладу."""

from datetime import date, time

from pydantic import BaseModel, ConfigDict, Field

from app.models import Parity
from app.services.schedule_view import LessonStatus


class RoomView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    building_code: str
    building_name: str
    floor: int | None = None


class TeacherView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    short_name: str
    degree: str | None = None
    position: str | None = None
    is_substitute: bool = False


class LessonView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    entry_id: int
    pair_number: int
    pair_label: str | None
    starts_at: time
    ends_at: time
    day_of_week: int
    week_parity: Parity
    subject_name: str
    subject_short: str | None
    lesson_type_code: str
    lesson_type_name: str
    lesson_type_short: str | None
    teachers: list[TeacherView] = Field(default_factory=list)
    rooms: list[RoomView] = Field(default_factory=list)
    groups: list[str] = Field(default_factory=list)
    subgroups: list[str] = Field(default_factory=list)
    streams: list[str] = Field(default_factory=list)
    note: str | None = None
    status: LessonStatus = LessonStatus.NORMAL
    change_reason: str | None = None
    moved_to: date | None = None
    moved_from: date | None = None


class DayView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    day: date
    day_of_week: int
    semester_id: int | None
    semester_name: str | None
    week_number: int | None
    parity: Parity | None
    is_working: bool
    closed_reason: str | None
    lessons: list[LessonView] = Field(default_factory=list)


class WeekView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    starts_on: date
    ends_on: date
    semester_id: int | None
    semester_name: str | None
    week_number: int | None
    parity: Parity | None
    days: list[DayView] = Field(default_factory=list)


# ---------- довідники для публічних фільтрів ----------


class GroupOption(BaseModel):
    id: int
    name: str
    course: int | None = None
    department_id: int | None = None
    department_name: str | None = None
    faculty_id: int | None = None
    faculty_name: str | None = None
    faculty_short_name: str | None = None


class SubgroupOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str


class TeacherOption(BaseModel):
    id: int
    full_name: str
    short_name: str
    degree: str | None = None
    position: str | None = None
    department_names: list[str] = Field(default_factory=list)


class RoomOption(BaseModel):
    id: int
    number: str
    building_id: int
    building_code: str
    building_name: str
    floor: int | None = None
    capacity: int | None = None


class LessonTypeOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    short_name: str | None = None


class PairTimeOption(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    starts_at: time
    ends_at: time
    label: str | None = None


class CalendarInfo(BaseModel):
    """Де ми зараз у календарі: семестр, номер тижня, парність."""

    day: date
    semester_id: int | None
    semester_name: str | None
    semester_start: date | None
    semester_end: date | None
    week_number: int | None
    parity: Parity | None
    week_starts_on: date | None
    week_ends_on: date | None
    is_working: bool
    closed_reason: str | None
