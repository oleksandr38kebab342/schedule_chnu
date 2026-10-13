from pydantic import BaseModel, ConfigDict, Field


class FacultyCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=32)
    short_name: str | None = Field(default=None, max_length=64)


class FacultyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=64)
    is_active: bool | None = None


class FacultyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    short_name: str | None
    is_active: bool


class DepartmentCreate(BaseModel):
    faculty_id: int
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=32)
    short_name: str | None = Field(default=None, max_length=64)
    parent_id: int | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    short_name: str | None = Field(default=None, max_length=64)
    parent_id: int | None = None
    is_active: bool | None = None


class DepartmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    faculty_id: int
    name: str
    code: str
    short_name: str | None
    parent_id: int | None
    is_active: bool
