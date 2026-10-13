"""Запис подій у журнал аудиту (ТЗ, розділ 42)."""

from typing import Any

from sqlalchemy.orm import Session

from app.models import AuditLog


def record(
    db: Session,
    *,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None = None,
    old_value: Any | None = None,
    new_value: Any | None = None,
    reason: str | None = None,
) -> AuditLog:
    """Додає запис у сесію (без commit — його робить виклична сторона)."""
    log = AuditLog(
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        old_value=old_value,
        new_value=new_value,
        reason=reason,
    )
    db.add(log)
    return log
