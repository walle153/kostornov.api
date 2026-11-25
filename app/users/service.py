"""Бизнес-логика модуля users."""

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.database import DatabaseSession, utc_now
from app.users.models import User

CREDENTIAL_MISMATCH = HTTPException(
    status_code=401, detail="Неверное имя пользователя или пароль"
)


def hash_password(plain_password: str) -> str:
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher

    return PasswordHash(recommended=Argon2Hasher()).hash(plain_password)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    from pwdlib import PasswordHash
    from pwdlib.hashers.argon2 import Argon2Hasher

    return PasswordHash(recommended=Argon2Hasher()).verify(plain_password, stored_hash)


def find_by_username(db: DatabaseSession, username: str) -> User | None:
    return db.scalar(select(User).where(User.username == username))


def register_user(db: DatabaseSession, username: str, password: str) -> User:
    """Создаёт пользователя; занятое имя даёт 409 (в том числе при гонке)."""
    if find_by_username(db, username) is not None:
        raise HTTPException(status_code=409, detail="Имя пользователя уже занято")

    user = User(username=username, password_hash=hash_password(password), created_at=utc_now())
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Имя пользователя уже занято")
    db.refresh(user)
    return user


def rename_user(db: DatabaseSession, user: User, new_username: str) -> User:
    """Меняет имя. Текущее имя сохраняется без ошибки; чужое имя — 409."""
    if user.username == new_username:
        return user
    existing = find_by_username(db, new_username)
    if existing is not None and existing.id != user.id:
        raise HTTPException(status_code=409, detail="Имя пользователя уже занято")

    user.username = new_username
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Имя пользователя уже занято")
    db.refresh(user)
    return user
