"""Наповнює БД правами, ролями та початковим суперадміністратором.

Запуск (ідемпотентний, можна повторювати):
    python -m scripts.seed
"""

import sys

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core import permissions as perm
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models import Permission, Role, User, UserRole


def sync_permissions(db: Session) -> dict[str, Permission]:
    existing = {p.code: p for p in db.scalars(select(Permission))}
    for code, description in perm.ALL_PERMISSIONS.items():
        if code in existing:
            existing[code].description = description
        else:
            created = Permission(code=code, description=description)
            db.add(created)
            existing[code] = created
    db.flush()
    return existing


def sync_roles(db: Session, perms: dict[str, Permission]) -> dict[str, Role]:
    existing = {r.code: r for r in db.scalars(select(Role))}
    for code, spec in perm.ROLES.items():
        role = existing.get(code)
        if role is None:
            role = Role(code=code, name=str(spec["name"]))
            db.add(role)
            existing[code] = role
        else:
            role.name = str(spec["name"])
        role.permissions = [perms[c] for c in spec["permissions"]]  # type: ignore[union-attr]
    db.flush()
    return existing


def ensure_admin(db: Session, roles: dict[str, Role]) -> tuple[User, bool]:
    email = settings.seed_admin_email.lower()
    user = db.scalar(select(User).where(User.email == email))
    if user is not None:
        return user, False

    user = User(
        email=email,
        full_name="Суперадміністратор",
        password_hash=hash_password(settings.seed_admin_password),
        is_active=True,
    )
    db.add(user)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=roles[perm.SUPER_ADMIN].id))
    return user, True


def main() -> None:
    # Консоль Windows стартує в cp1252 і падає на кириличному виводі.
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    with SessionLocal() as db:
        perms = sync_permissions(db)
        roles = sync_roles(db, perms)
        admin, created = ensure_admin(db, roles)
        db.commit()

    print(f"Прав: {len(perms)}, ролей: {len(roles)}")
    if created:
        print(f"Створено суперадміністратора: {admin.email}")
        print("Пароль узято з SEED_ADMIN_PASSWORD — змініть його після першого входу.")
    else:
        print(f"Суперадміністратор уже існує: {admin.email}")


if __name__ == "__main__":
    main()
