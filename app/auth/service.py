"""Бизнес-логика модуля auth: сессии входа и токены."""

import hashlib
import secrets
from datetime import timedelta

from fastapi import HTTPException
from sqlalchemy import select

from app.auth.models import AuthSession
from app.database import DatabaseSession, utc_now
from app.users.models import User
from app.users.service import verify_password

SESSION_TTL = timedelta(hours=24)
SESSION_TTL_SECONDS = 24 * 60 * 60
COOKIE_NAME = "access_token"


def new_raw_token() -> str:
    """Непредсказуемый токен: 32 случайных байта (256 бит энтропии)."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    """SHA-256 хеш токена — ровно это хранится в БД."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def authenticate_user(db: DatabaseSession, username: str, password: str) -> User | None:
    """Проверяет учётные данные. Неверное имя и неверный пароль неотличимы."""
    user = db.scalar(select(User).where(User.username == username))
    if user is None or not verify_password(password, user.password_hash):
        return None
    return user


def start_session(db: DatabaseSession, user: User) -> str:
    """Создаёт сессию на 24 часа; в БД попадает только хеш токена."""
    raw_token = new_raw_token()
    now = utc_now()
    db.add(
        AuthSession(
            user_id=user.id,
            token_hash=hash_token(raw_token),
            created_at=now,
            expires_at=now + SESSION_TTL,
        )
    )
    db.commit()
    return raw_token


def find_session_user(db: DatabaseSession, raw_token: str) -> User | None:
    """Возвращает владельца действующей сессии или None (нет, отозвана, истекла)."""
    token_hash = hash_token(raw_token)
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == token_hash))
    if session is None:
        return None
    if session.expires_at <= utc_now():
        db.delete(session)
        db.commit()
        return None
    return db.get(User, session.user_id)


def end_session(db: DatabaseSession, raw_token: str) -> None:
    """Удаляет ровно одну сессию по токену текущего запроса."""
    session = db.scalar(select(AuthSession).where(AuthSession.token_hash == hash_token(raw_token)))
    if session is not None:
        db.delete(session)
        db.commit()
