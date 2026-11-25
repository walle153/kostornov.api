"""Единый механизм проверки Cookie/Bearer и получения текущего пользователя."""

from typing import Annotated

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyCookie, HTTPAuthorizationCredentials, HTTPBearer

from app.auth.service import COOKIE_NAME, find_session_user
from app.database import DatabaseSession
from app.users.models import User

WWW_AUTH_HEADERS = {"WWW-Authenticate": "Bearer"}


class StrictBearerHeader(HTTPBearer):
    """Парсит заголовок Authorization. Некорректный заголовок — 401 без перехода к Cookie."""

    async def __call__(self, request: Request) -> HTTPAuthorizationCredentials | None:
        raw_header = request.headers.get("Authorization")
        if raw_header is None:
            return None
        scheme, _, token = raw_header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise HTTPException(
                status_code=401,
                detail="Некорректный заголовок Authorization",
                headers=WWW_AUTH_HEADERS,
            )
        return HTTPAuthorizationCredentials(scheme="bearer", credentials=token.strip())


bearer_scheme = StrictBearerHeader(
    auto_error=False,
    scheme_name="BearerSession",
    description="Bearer-токен из POST /api/auth/login",
)
cookie_scheme = APIKeyCookie(
    name=COOKIE_NAME,
    auto_error=False,
    scheme_name="CookieSession",
    description="Cookie access_token, устанавливается при входе",
)


def get_current_user(
    db: DatabaseSession,
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    cookie_token: str | None = Security(cookie_scheme),
) -> User:
    """Приоритет: Authorization > Cookie. Нет или недействительный токен — 401."""
    if bearer is not None:
        raw_token = bearer.credentials
    elif cookie_token is not None:
        raw_token = cookie_token
    else:
        raise HTTPException(
            status_code=401,
            detail="Требуется авторизация: Bearer-токен или Cookie",
            headers=WWW_AUTH_HEADERS,
        )

    user = find_session_user(db, raw_token)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Сессия недействительна или истекла",
            headers=WWW_AUTH_HEADERS,
        )
    return user


CurrentUser = Annotated[User, Security(get_current_user)]
