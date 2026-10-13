from typing import Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin

# JSONB у Postgres, звичайний JSON у SQLite (тести).
JsonType = JSON().with_variant(JSONB(), "postgresql")


class AuditLog(Base, TimestampMixin):
    """Журнал змін: override, зміни прав, імпорт, масові операції (ТЗ, розділ 42)."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    entity_id: Mapped[int | None] = mapped_column(Integer)
    old_value: Mapped[Any | None] = mapped_column(JsonType)
    new_value: Mapped[Any | None] = mapped_column(JsonType)
    reason: Mapped[str | None] = mapped_column(String(500))


class SystemSetting(Base, TimestampMixin):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    value: Mapped[Any | None] = mapped_column(JsonType)
    description: Mapped[str | None] = mapped_column(String(255))
