"""HTTP-маршруты модуля users."""

from fastapi import APIRouter

from app.auth.dependencies import CurrentUser
from app.database import DatabaseSession
from app.users.schemas import RegisterRequest, UserResponse, UsernameChangeRequest
from app.users.service import register_user, rename_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.post("/register", status_code=201, response_model=UserResponse, summary="Регистрация пользователя")
def register(payload: RegisterRequest, db: DatabaseSession):
    return register_user(db, payload.username, payload.password)


@router.get("/me", response_model=UserResponse, summary="Свой профиль")
def read_profile(current_user: CurrentUser):
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Изменение своего имени")
def update_profile(payload: UsernameChangeRequest, db: DatabaseSession, current_user: CurrentUser):
    return rename_user(db, current_user, payload.username)
