"""ORM-модель пользователя."""

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class User(Base):
    """Учётная запись: уникальное имя и хеш пароля."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)

    tasks = relationship("Task", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("AuthSession", back_populates="owner", cascade="all, delete-orphan")
