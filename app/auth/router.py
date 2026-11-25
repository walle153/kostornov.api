"""HTTP-маршруты модуля auth."""

from fastapi import APIRouter, HTTPException, Response, Security
from fastapi.security import HTTPAuthorizationCredentials

from app.auth.dependencies import (
    CurrentUser,
    bearer_scheme,
    cookie_scheme,
)
from app.auth.schemas import LoginRequest, TokenResponse
from app.auth.service import (
    COOKIE_NAME,
    SESSION_TTL_SECONDS,
    authenticate_user,
    end_session,
    start_session,
)
from app.database import DatabaseSession

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse, summary="Вход и получение токена")
def login(payload: LoginRequest, response: Response, db: DatabaseSession):
    user = authenticate_user(db, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Неверное имя пользователя или пароль")

    raw_token = start_session(db, user)
    response.set_cookie(
        key=COOKIE_NAME,
        value=raw_token,
        max_age=SESSION_TTL_SECONDS,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return TokenResponse(
        access_token=raw_token, token_type="bearer", expires_in=SESSION_TTL_SECONDS
    )


@router.post("/logout", status_code=204, summary="Выход, отзыв текущей сессии")
def logout(
    response: Response,
    db: DatabaseSession,
    current_user: CurrentUser,
    bearer: HTTPAuthorizationCredentials | None = Security(bearer_scheme),
    cookie_token: str | None = Security(cookie_scheme),
):
    raw_token = bearer.credentials if bearer is not None else cookie_token
    end_session(db, raw_token)
    response.delete_cookie(key=COOKIE_NAME, path="/")
