from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models import ConflictKind, ConflictSeverity, Parity


class ScheduleEntryCreate(BaseModel):
    semester_id: int
    subject_id: int
    lesson_type_id: int
    pair_time_id: int
    day_of_week: int = Field(ge=1, le=7)
    week_parity: Parity
    note: str | None = Field(default=None, max_length=255)

    teacher_ids: list[int] = Field(default_factory=list)
    room_ids: list[int] = Field(default_factory=list)
    group_ids: list[int] = Field(default_factory=list)
    subgroup_ids: list[int] = Field(default_factory=list)
    stream_ids: list[int] = Field(default_factory=list)

    # Якщо задано — зберегти попри конфлікт із цією причиною (потрібне право).
    override_reason: str | None = Field(default=None, max_length=500)

    @model_validator(mode="after")
    def _at_least_one_audience(self) -> "ScheduleEntryCreate":
        if not (self.group_ids or self.subgroup_ids or self.stream_ids):
            raise ValueError("Потрібно вказати хоча б одну групу, підгрупу або потік")
        return self


class ConflictRead(BaseModel):
    kind: ConflictKind
    severity: ConflictSeverity
    resource_id: int
    other_entry_id: int
    details: str


class ScheduleEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    semester_id: int
    subject_id: int
    lesson_type_id: int
    pair_time_id: int
    day_of_week: int
    week_parity: Parity
    note: str | None
    teacher_ids: list[int] = Field(default_factory=list)
    room_ids: list[int] = Field(default_factory=list)
    group_ids: list[int] = Field(default_factory=list)
    subgroup_ids: list[int] = Field(default_factory=list)
    stream_ids: list[int] = Field(default_factory=list)


class ScheduleEntryCreateResult(BaseModel):
    entry: ScheduleEntryRead | None
    conflicts: list[ConflictRead] = Field(default_factory=list)
    saved: bool
    overridden: bool = False
