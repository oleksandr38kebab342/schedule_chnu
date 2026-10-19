"""Журнал аудиту: хто, коли і що змінив (ТЗ, розділ 42)."""

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import require_permission
from app.core import permissions
from app.core.database import get_db
from app.models import AuditLog, User

router = APIRouter(prefix="/audit", tags=["audit"])
view_perm = require_permission(permissions.AUDIT_VIEW)


class AuditLogRead(BaseModel):
    id: int
    created_at: datetime
    user_id: int | None
    user_email: str | None
    action: str
    entity_type: str
    entity_id: int | None
    old_value: Any | None
    new_value: Any | None
    reason: str | None


@router.get("", response_model=list[AuditLogRead])
def list_logs(
    action: str | None = Query(default=None),
    entity_type: str | None = Query(default=None),
    entity_id: int | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _=Depends(view_perm),
) -> list[AuditLogRead]:
    stmt = select(AuditLog).order_by(AuditLog.id.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type:
        stmt = stmt.where(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)

    logs = list(db.scalars(stmt.offset(offset).limit(limit)))
    emails = {
        u.id: u.email
        for u in db.scalars(select(User).where(User.id.in_({l.user_id for l in logs if l.user_id})))
    }
    return [
        AuditLogRead(
            id=log.id,
            created_at=log.created_at,
            user_id=log.user_id,
            user_email=emails.get(log.user_id) if log.user_id else None,
            action=log.action,
            entity_type=log.entity_type,
            entity_id=log.entity_id,
            old_value=log.old_value,
            new_value=log.new_value,
            reason=log.reason,
        )
        for log in logs
    ]
