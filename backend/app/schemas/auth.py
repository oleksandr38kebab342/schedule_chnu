from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.security import MAX_PASSWORD_BYTES


class LoginRequest(BaseModel):
    email: EmailStr
    # Мінімальна довжина тут не перевіряється: політика паролів діє при їх
    # встановленні, а вхід на будь-який непідходящий пароль має давати 401,
    # а не 422, щоб не розкривати вимоги й не блокувати старі паролі.
    password: str = Field(min_length=1, max_length=MAX_PASSWORD_BYTES)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class CurrentUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    full_name: str
    is_active: bool
    roles: list[str]
    permissions: list[str]
