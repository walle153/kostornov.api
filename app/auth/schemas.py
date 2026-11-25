"""Схемы Pydantic модуля auth."""

from pydantic import BaseModel, ConfigDict, Field

from app.users.schemas import USERNAME_PATTERN


class LoginRequest(BaseModel):
    """Тело входа: те же ограничения длины, что и при регистрации."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32, examples=["student01"])
    password: str = Field(min_length=8, max_length=128, examples=["secret123"])


class TokenResponse(BaseModel):
    """Ответ успешного входа."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
