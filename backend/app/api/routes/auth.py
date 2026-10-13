from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.core.database import get_db
from app.core.security import create_access_token, verify_password
from app.models import User
from app.schemas.auth import CurrentUser, LoginRequest, TokenResponse

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))

    # Однакова відповідь для неіснуючого email і хибного пароля, щоб не
    # розкривати, які адреси зареєстровані.
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Невірний email або пароль",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Користувача деактивовано",
        )

    return TokenResponse(access_token=create_access_token(user.id))


@router.get("/me", response_model=CurrentUser)
def me(user: User = Depends(get_current_user)) -> CurrentUser:
    return CurrentUser(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
        roles=user.role_codes,
        permissions=sorted(user.permission_codes),
    )
