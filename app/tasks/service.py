"""Бизнес-логика модуля tasks: CRUD, фильтрация, поиск, пагинация."""

from fastapi import HTTPException
from sqlalchemy import func, select

from app.database import DatabaseSession, utc_now
from app.tasks.models import TASK_PRIORITIES, TASK_STATUSES, Task
from app.users.models import User

NOT_FOUND = HTTPException(status_code=404, detail="Задача не найдена")
EMPTY_PATCH = HTTPException(
    status_code=422, detail="Необходимо передать хотя бы одно изменяемое поле"
)


def create_task(db: DatabaseSession, owner: User, payload) -> Task:
    """Создаёт задачу: владелец и метки времени назначаются сервером."""
    now = utc_now()
    task = Task(
        user_id=owner.id,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        priority=payload.priority,
        due_date=payload.due_date,
        created_at=now,
        updated_at=now,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def _filtered_statement(owner: User, status: str | None, priority: str | None, search: str | None):
    stmt = select(Task).where(Task.user_id == owner.id)
    if status is not None:
        stmt = stmt.where(Task.status == status)
    if priority is not None:
        stmt = stmt.where(Task.priority == priority)
    if search:
        stmt = stmt.where(Task.title.contains(search, autoescape=True))
    return stmt


def list_tasks(
    db: DatabaseSession,
    owner: User,
    status: str | None,
    priority: str | None,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Task], int]:
    """Фильтры и сортировка применяются до пагинации; total их учитывает."""
    stmt = _filtered_statement(owner, status, priority, search)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    items = db.scalars(stmt.order_by(Task.id.desc()).limit(limit).offset(offset)).all()
    return items, total


def get_task_or_404(db: DatabaseSession, owner: User, task_id: int) -> Task:
    """Чужая и несуществующая задача неразличимы — всегда 404."""
    task = db.get(Task, task_id)
    if task is None or task.user_id != owner.id:
        raise NOT_FOUND
    return task


def update_task(db: DatabaseSession, task: Task, payload) -> Task:
    """Частичное изменение. Явный null разрешён только для description и due_date."""
    patch = payload.model_dump(exclude_unset=True)
    if not patch:
        raise EMPTY_PATCH

    for field in ("title", "status", "priority"):
        if field in patch:
            if patch[field] is None:
                raise HTTPException(status_code=422, detail=f"Поле {field} не может быть null")
            setattr(task, field, patch[field])
    for field in ("description", "due_date"):
        if field in patch:
            setattr(task, field, patch[field])

    task.updated_at = utc_now()
    db.commit()
    db.refresh(task)
    return task


def delete_task(db: DatabaseSession, task: Task) -> None:
    db.delete(task)
    db.commit()


__all__ = [
    "TASK_PRIORITIES",
    "TASK_STATUSES",
    "create_task",
    "delete_task",
    "get_task_or_404",
    "list_tasks",
    "update_task",
]
