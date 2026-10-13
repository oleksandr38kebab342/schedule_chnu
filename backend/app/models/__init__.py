from app.models.academic import (
    Group,
    LessonType,
    Stream,
    StreamGroup,
    Subgroup,
    Subject,
    SubjectDepartment,
    natural_key,
)
from app.models.audit import AuditLog, SystemSetting
from app.models.auth import Permission, Role, User, UserRole, role_permissions
from app.models.base import Base, TimestampMixin
from app.models.calendar import (
    AcademicWeek,
    AcademicYear,
    CalendarException,
    ExceptionKind,
    Parity,
    Semester,
)
from app.models.facilities import (
    Building,
    PairTime,
    Room,
    RoomAlias,
    normalize_room_code,
)
from app.models.organization import Department, Faculty, Teacher, TeacherDepartment
from app.models.schedule import (
    ConflictKind,
    ConflictSeverity,
    ExceptionAction,
    ScheduleConflict,
    ScheduleConflictOverride,
    ScheduleEntry,
    ScheduleException,
    ScheduleGroup,
    ScheduleRoom,
    ScheduleStream,
    ScheduleSubgroup,
    ScheduleTeacher,
)

__all__ = [
    "Base",
    "TimestampMixin",
    # auth
    "Permission",
    "Role",
    "User",
    "UserRole",
    "role_permissions",
    # organization
    "Faculty",
    "Department",
    "Teacher",
    "TeacherDepartment",
    # academic
    "Group",
    "Subgroup",
    "Stream",
    "StreamGroup",
    "LessonType",
    "Subject",
    "SubjectDepartment",
    "natural_key",
    # facilities
    "Building",
    "Room",
    "RoomAlias",
    "PairTime",
    "normalize_room_code",
    # calendar
    "AcademicYear",
    "Semester",
    "AcademicWeek",
    "CalendarException",
    "Parity",
    "ExceptionKind",
    # schedule
    "ScheduleEntry",
    "ScheduleTeacher",
    "ScheduleRoom",
    "ScheduleGroup",
    "ScheduleSubgroup",
    "ScheduleStream",
    "ScheduleException",
    "ScheduleConflict",
    "ScheduleConflictOverride",
    "ExceptionAction",
    "ConflictKind",
    "ConflictSeverity",
    # audit
    "AuditLog",
    "SystemSetting",
]
