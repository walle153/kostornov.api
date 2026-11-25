"""Схемы Pydantic модуля users."""

from datetime import datetime, timezone
from typing import Callable

from pydantic import BaseModel, ConfigDict, Field, field_serializer

USERNAME_PATTERN = r"^[a-z0-9_]{3,32}$"


def format_utc(value: datetime) -> str:
    """ISO 8601 в UTC с суффиксом Z."""
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat().replace("+00:00", "Z")


class RegisterRequest(BaseModel):
    """Тело регистрации."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(
        min_length=3,
        max_length=32,
        pattern=USERNAME_PATTERN,
        description="3-32 символа: латиница в нижнем регистре, цифры, подчёркивание",
        examples=["student01"],
    )
    password: str = Field(min_length=8, max_length=128, examples=["secret123"])


class UsernameChangeRequest(BaseModel):
    """Тело смены имени: единственное изменяемое поле профиля."""

    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=32, pattern=USERNAME_PATTERN)


class UserResponse(BaseModel):
    """Публичное описание пользователя без пароля и его хеша."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, value: datetime, _info) -> str:
        return format_utc(value)
