"""Схемы Pydantic модуля tasks."""

from datetime import date, datetime, timezone
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
)

from app.users.schemas import format_utc

TaskStatus = Literal["pending", "in_progress", "completed"]
TaskPriority = Literal["low", "medium", "high"]


class TaskBase(BaseModel):
    """Общие правила полей задачи."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=150, examples=["Подготовить отчёт"])
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus = "pending"
    priority: TaskPriority = "medium"
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("название не может состоять только из пробелов")
        return stripped


class TaskCreateRequest(TaskBase):
    """Тело создания задачи. id, владелец и метки времени назначает сервер."""


class TaskPatchRequest(BaseModel):
    """Тело частичного изменения задачи (пустой объект запрещён)."""

    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=2000)
    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    due_date: date | None = None

    @field_validator("title")
    @classmethod
    def title_not_blank(cls, value: str | None) -> str | None:
        if value is None:
            return value
        stripped = value.strip()
        if not stripped:
            raise ValueError("название не может состоять только из пробелов")
        return stripped


class TaskResponse(BaseModel):
    """Публичное описание задачи."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    due_date: date | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("created_at", "updated_at")
    def serialize_datetime(self, value: datetime, _info) -> str:
        return format_utc(value)


class TaskListResponse(BaseModel):
    """Постраничная выдача задач."""

    items: list[TaskResponse]
    total: int
    limit: int
    offset: int
