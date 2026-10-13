"""Довідник прав і базова розкладка прав по ролях (ТЗ, розділи 3-4).

Перелік свідомо ширший за реалізовані ендпоінти: він фіксує цільову
permission-модель, на яку спиратимуться наступні спринти.
"""

SCHEDULE_VIEW = "schedule.view"
SCHEDULE_CREATE = "schedule.create"
SCHEDULE_EDIT = "schedule.edit"
SCHEDULE_DELETE = "schedule.delete"
SCHEDULE_MOVE = "schedule.move"
SCHEDULE_CANCEL = "schedule.cancel"
SCHEDULE_OVERRIDE_CONFLICT = "schedule.override_conflict"
SCHEDULE_IMPORT = "schedule.import"
SCHEDULE_EXPORT = "schedule.export"

FACULTY_MANAGE = "faculty.manage"
DEPARTMENT_MANAGE = "department.manage"
TEACHER_MANAGE = "teacher.manage"
GROUP_MANAGE = "group.manage"
SUBJECT_MANAGE = "subject.manage"
ROOM_MANAGE = "room.manage"
CALENDAR_MANAGE = "calendar.manage"

USERS_MANAGE = "users.manage"
ROLES_MANAGE = "roles.manage"
SETTINGS_MANAGE = "settings.manage"
AUDIT_VIEW = "audit.view"

ALL_PERMISSIONS: dict[str, str] = {
    SCHEDULE_VIEW: "Перегляд розкладу",
    SCHEDULE_CREATE: "Створення занять",
    SCHEDULE_EDIT: "Редагування занять",
    SCHEDULE_DELETE: "Видалення занять",
    SCHEDULE_MOVE: "Перенесення занять",
    SCHEDULE_CANCEL: "Скасування занять",
    SCHEDULE_OVERRIDE_CONFLICT: "Збереження попри конфлікт",
    SCHEDULE_IMPORT: "Імпорт розкладу",
    SCHEDULE_EXPORT: "Експорт розкладу",
    FACULTY_MANAGE: "Керування факультетами",
    DEPARTMENT_MANAGE: "Керування кафедрами",
    TEACHER_MANAGE: "Керування викладачами",
    GROUP_MANAGE: "Керування групами",
    SUBJECT_MANAGE: "Керування дисциплінами",
    ROOM_MANAGE: "Керування аудиторіями",
    CALENDAR_MANAGE: "Керування академічним календарем",
    USERS_MANAGE: "Керування користувачами",
    ROLES_MANAGE: "Керування ролями й правами",
    SETTINGS_MANAGE: "Системні налаштування",
    AUDIT_VIEW: "Перегляд журналу аудиту",
}

SUPER_ADMIN = "super_admin"
CHIEF_ADMIN = "chief_admin"
FACULTY_ADMIN = "faculty_admin"
DEPARTMENT_ADMIN = "department_admin"
DISPATCHER = "dispatcher"
TEACHER = "teacher"
STUDENT = "student"

_SCHEDULE_FULL = [
    SCHEDULE_VIEW,
    SCHEDULE_CREATE,
    SCHEDULE_EDIT,
    SCHEDULE_DELETE,
    SCHEDULE_MOVE,
    SCHEDULE_CANCEL,
    SCHEDULE_OVERRIDE_CONFLICT,
    SCHEDULE_IMPORT,
    SCHEDULE_EXPORT,
]

_REFERENCE_FULL = [
    FACULTY_MANAGE,
    DEPARTMENT_MANAGE,
    TEACHER_MANAGE,
    GROUP_MANAGE,
    SUBJECT_MANAGE,
    ROOM_MANAGE,
    CALENDAR_MANAGE,
]

ROLES: dict[str, dict[str, object]] = {
    SUPER_ADMIN: {
        "name": "Суперадміністратор",
        "permissions": list(ALL_PERMISSIONS),
    },
    CHIEF_ADMIN: {
        "name": "Головний адміністратор",
        "permissions": [*_SCHEDULE_FULL, *_REFERENCE_FULL, USERS_MANAGE, AUDIT_VIEW],
    },
    FACULTY_ADMIN: {
        "name": "Адміністратор факультету",
        "permissions": [*_SCHEDULE_FULL, *_REFERENCE_FULL, AUDIT_VIEW],
    },
    DEPARTMENT_ADMIN: {
        "name": "Адміністратор кафедри",
        "permissions": [
            SCHEDULE_VIEW,
            SCHEDULE_EXPORT,
            DEPARTMENT_MANAGE,
            TEACHER_MANAGE,
            GROUP_MANAGE,
            SUBJECT_MANAGE,
        ],
    },
    DISPATCHER: {
        "name": "Диспетчер розкладу",
        "permissions": list(_SCHEDULE_FULL),
    },
    TEACHER: {
        "name": "Викладач",
        "permissions": [SCHEDULE_VIEW],
    },
    STUDENT: {
        "name": "Студент",
        "permissions": [SCHEDULE_VIEW],
    },
}
