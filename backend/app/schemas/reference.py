from datetime import time

from pydantic import BaseModel, ConfigDict, Field


# ---------- Teachers ----------
class TeacherCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    middle_name: str | None = Field(default=None, max_length=128)
    degree: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=128)
    department_ids: list[int] = Field(default_factory=list)
    primary_department_id: int | None = None


class TeacherUpdate(BaseModel):
    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    middle_name: str | None = Field(default=None, max_length=128)
    degree: str | None = Field(default=None, max_length=128)
    position: str | None = Field(default=None, max_length=128)
    is_active: bool | None = None


class TeacherRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    middle_name: str | None
    full_name: str
    degree: str | None
    position: str | None
    is_active: bool
    department_ids: list[int] = Field(default_factory=list)


# ---------- Groups / subgroups / streams ----------
class GroupCreate(BaseModel):
    department_id: int
    name: str = Field(min_length=1, max_length=64)
    course: int | None = Field(default=None, ge=1, le=10)
    students_count: int | None = Field(default=None, ge=0)


class GroupUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    course: int | None = Field(default=None, ge=1, le=10)
    students_count: int | None = Field(default=None, ge=0)
    is_active: bool | None = None


class GroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    department_id: int
    name: str
    course: int | None
    students_count: int | None
    is_active: bool


class SubgroupCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)


class SubgroupRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    group_id: int
    name: str


class StreamCreate(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    group_ids: list[int] = Field(default_factory=list)


class StreamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    is_active: bool
    group_ids: list[int] = Field(default_factory=list)


# ---------- Subjects / lesson types ----------
class SubjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=32)
    short_name: str | None = Field(default=None, max_length=64)
    department_ids: list[int] = Field(default_factory=list)


class SubjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    short_name: str | None
    is_active: bool


class LessonTypeCreate(BaseModel):
    code: str = Field(min_length=1, max_length=32)
    name: str = Field(min_length=1, max_length=128)
    short_name: str | None = Field(default=None, max_length=32)


class LessonTypeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    short_name: str | None


# ---------- Buildings / rooms / times ----------
class BuildingCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=32)
    address: str | None = Field(default=None, max_length=255)


class BuildingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    address: str | None


class RoomCreate(BaseModel):
    building_id: int
    number: str = Field(min_length=1, max_length=64)
    capacity: int | None = Field(default=None, ge=0)
    room_type: str | None = Field(default=None, max_length=64)
    floor: int | None = None
    aliases: list[str] = Field(default_factory=list)


class RoomRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    building_id: int
    number: str
    normalized: str
    capacity: int | None
    room_type: str | None
    floor: int | None
    is_active: bool
    aliases: list[str] = Field(default_factory=list)


class PairTimeCreate(BaseModel):
    number: int = Field(ge=1, le=20)
    starts_at: time
    ends_at: time
    label: str | None = Field(default=None, max_length=64)


class PairTimeUpdate(BaseModel):
    starts_at: time | None = None
    ends_at: time | None = None
    label: str | None = Field(default=None, max_length=64)


class PairTimeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: int
    starts_at: time
    ends_at: time
    label: str | None
