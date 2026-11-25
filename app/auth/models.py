"""ORM-модель сессии авторизации."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utc_now


class AuthSession(Base):
    """Серверная сессия входа. Хранит только SHA-256 хеш токена."""

    __tablename__ = "auth_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=utc_now)
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    owner = relationship("User", back_populates="sessions")
