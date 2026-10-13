from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.models import ExceptionKind, Parity


class AcademicYearCreate(BaseModel):
    name: str = Field(min_length=1, max_length=32)
    starts_on: date
    ends_on: date


class AcademicYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    starts_on: date
    ends_on: date


class SemesterCreate(BaseModel):
    academic_year_id: int
    ordinal: int = Field(ge=1, le=2)
    name: str = Field(min_length=1, max_length=64)
    start_date: date
    end_date: date
    first_week_parity: Parity = Parity.ODD


class SemesterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    academic_year_id: int
    ordinal: int
    name: str
    start_date: date
    end_date: date
    first_week_parity: Parity


class AcademicWeekRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    semester_id: int
    number: int
    parity: Parity
    starts_on: date
    ends_on: date


class WeekForDateRead(BaseModel):
    number: int
    parity: Parity
    starts_on: date
    ends_on: date


class CalendarExceptionCreate(BaseModel):
    kind: ExceptionKind
    date_from: date
    date_to: date
    description: str | None = Field(default=None, max_length=255)


class CalendarExceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    semester_id: int
    kind: ExceptionKind
    date_from: date
    date_to: date
    description: str | None
