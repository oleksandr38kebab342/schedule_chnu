from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models import User

bearer_scheme = HTTPBearer(auto_error=False)

_CREDENTIALS_ERROR = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Недійсний або відсутній токен доступу",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise _CREDENTIALS_ERROR

    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise _CREDENTIALS_ERROR

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise _CREDENTIALS_ERROR

    return user


def require_permission(code: str) -> Callable[[User], User]:
    """Залежність, що пропускає лише користувача з конкретним правом."""

    def dependency(user: User = Depends(get_current_user)) -> User:
        if code not in user.permission_codes:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостатньо прав: потрібне {code}",
            )
        return user

    return dependency
