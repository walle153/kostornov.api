"""HTTP-маршруты модуля tasks."""

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query
from pydantic import StringConstraints

from app.auth.dependencies import CurrentUser
from app.database import DatabaseSession
from app.tasks.schemas import (
    TaskCreateRequest,
    TaskListResponse,
    TaskPatchRequest,
    TaskPriority,
    TaskResponse,
    TaskStatus,
)
from app.tasks.service import (
    create_task,
    delete_task,
    get_task_or_404,
    list_tasks,
    update_task,
)

SearchString = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=150),
]

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


@router.post("", status_code=201, response_model=TaskResponse, summary="Создание задачи")
def create_task_route(payload: TaskCreateRequest, db: DatabaseSession, current_user: CurrentUser):
    return create_task(db, current_user, payload)


@router.get("", response_model=TaskListResponse, summary="Список своих задач")
def list_tasks_route(
    db: DatabaseSession,
    current_user: CurrentUser,
    status: TaskStatus | None = Query(default=None, description="Точный фильтр по статусу"),
    priority: TaskPriority | None = Query(default=None, description="Точный фильтр по приоритету"),
    search: SearchString | None = Query(default=None, description="Подстрока в названии задачи"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    items, total = list_tasks(db, current_user, status, priority, search, limit, offset)
    return TaskListResponse(items=items, total=total, limit=limit, offset=offset)


@router.get("/{task_id}", response_model=TaskResponse, summary="Получение задачи")
def read_task_route(
    task_id: Annotated[int, Path(ge=1)],
    db: DatabaseSession,
    current_user: CurrentUser,
):
    return get_task_or_404(db, current_user, task_id)


@router.patch("/{task_id}", response_model=TaskResponse, summary="Частичное изменение задачи")
def update_task_route(
    task_id: Annotated[int, Path(ge=1)],
    payload: TaskPatchRequest,
    db: DatabaseSession,
    current_user: CurrentUser,
):
    task = get_task_or_404(db, current_user, task_id)
    return update_task(db, task, payload)


@router.delete("/{task_id}", status_code=204, summary="Удаление задачи")
def delete_task_route(
    task_id: Annotated[int, Path(ge=1)],
    db: DatabaseSession,
    current_user: CurrentUser,
):
    task = get_task_or_404(db, current_user, task_id)
    delete_task(db, task)
