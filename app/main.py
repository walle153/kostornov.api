"""Точка входа приложения Task Manager API."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app import database
from app.auth.router import router as auth_router
from app.tasks.router import router as tasks_router
from app.users.router import router as users_router


@asynccontextmanager
async def lifespan(_: FastAPI):
    database.create_tables()
    yield


app = FastAPI(
    title="Task Manager API",
    description=(
        "Серверное REST API «Менеджер управления задачами»: учётные записи, "
        "сессии авторизации (Cookie и Bearer) и персональные задачи."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.include_router(users_router)
app.include_router(auth_router)
app.include_router(tasks_router)


@app.get("/api/health", tags=["service"], summary="Проверка доступности")
def check_health():
    """Открытый маршрут: доступность приложения."""
    return {"status": "ok"}


@app.exception_handler(Exception)
async def handle_unexpected_error(_request, _exc):
    """Непредвиденные ошибки не раскрывают traceback клиенту."""
    return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера"})
