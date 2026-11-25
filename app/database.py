"""Подключение к SQLite, декларативная база и жизненный цикл сессий SQLAlchemy."""

from datetime import datetime, timezone
from typing import Annotated

import sqlalchemy
from fastapi import Depends
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

DATABASE_URL = "sqlite:///./taskbox.db"

engine = sqlalchemy.create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)


@sqlalchemy.event.listens_for(engine, "connect")
def _enable_foreign_keys(dbapi_connection, _connection_record):
    """Включаем реальный контроль внешних ключей в SQLite."""
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


class Base(DeclarativeBase):
    """Общий декларативный базовый класс всех ORM-моделей."""


SessionFactory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def utc_now() -> datetime:
    """Текущее время UTC. В БД хранится наивное значение в UTC."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def get_db():
    """Сессия БД на время обработки одного запроса."""
    db_session = SessionFactory()
    try:
        yield db_session
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


DatabaseSession = Annotated[Session, Depends(get_db)]


def create_tables() -> None:
    """Создаёт файл БД и все таблицы при первом запуске; данные не затирает."""
    from app.auth.models import AuthSession  # noqa: F401
    from app.tasks.models import Task  # noqa: F401
    from app.users.models import User  # noqa: F401

    Base.metadata.create_all(engine)
