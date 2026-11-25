# Task Manager API

Серверное REST API «Менеджер управления задачами» (учебная практика, ИС 24/9-3).

Реализует регистрация пользователей, сессии авторизации (Cookie и Bearer-токен)
и работу с персональным списком задач. Каждый пользователь видит только свои
задачи, данные сохраняются в SQLite и переживают перезапуск сервера.

## Стек

- Python 3.11+
- FastAPI — маршрутизация, зависимости, OpenAPI/Swagger
- Uvicorn — ASGI-сервер
- SQLAlchemy 2.x (синхронный режим) — ORM
- SQLite 3 — файловая БД `taskbox.db`
- Pydantic 2.x — схемы запросов, ответов и валидация
- pwdlib[argon2] — хеширование паролей
- Стандартная библиотека — токены (secrets), SHA-256 (hashlib)

## Запуск в VS Code

1. Откройте папку проекта в VS Code, затем терминал (Ctrl+`).
2. Создайте и активируйте виртуальное окружение:

```bash
python -m venv .venv
# Windows (PowerShell):
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate
```

3. Установите зависимости:

```bash
pip install -r requirements.txt
```

4. Запустите сервер:

```bash
uvicorn app.main:app --reload
```

При первом запуске БД `taskbox.db` и все таблицы создаются автоматически.
Повторный запуск данные не очищает.

5. Откройте в браузере интерактивную документацию:
   - Swagger UI: http://127.0.0.1:8000/docs
   - OpenAPI-схема: http://127.0.0.1:8000/openapi.json
   - Проверка доступности: GET http://127.0.0.1:8000/api/health

## Структура проекта

```
task-manager-api/
├── app/
│   ├── __init__.py
│   ├── main.py          # точка входа, маршрутизаторы, инициализация БД
│   ├── database.py      # SQLite, декларативная база, сессии SQLAlchemy
│   ├── users/           # регистрация, профиль
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   └── router.py
│   ├── auth/            # вход, выход, сессии, текущий пользователь
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── service.py
│   │   ├── dependencies.py
│   │   └── router.py
│   └── tasks/           # CRUD задач, фильтрация, поиск, пагинация
│       ├── models.py
│       ├── schemas.py
│       ├── service.py
│       └── router.py
├── requirements.txt
├── README.md
└── .gitignore
```

## Маршруты API

| Метод | Путь | Доступ | Назначение | Успех |
| --- | --- | --- | --- | --- |
| GET | `/api/health` | открытый | проверка доступности | 200 |
| POST | `/api/users/register` | открытый | регистрация | 201 |
| POST | `/api/auth/login` | открытый | вход, токен в JSON и Cookie | 200 |
| POST | `/api/auth/logout` | защищённый | отзыв текущей сессии | 204 |
| GET | `/api/users/me` | защищённый | свой профиль | 200 |
| PATCH | `/api/users/me` | защищённый | изменение своего имени | 200 |
| POST | `/api/tasks` | защищённый | создание задачи | 201 |
| GET | `/api/tasks` | защищённый | список задач (фильтры, поиск, пагинация) | 200 |
| GET | `/api/tasks/{task_id}` | защищённый | получение задачи | 200 |
| PATCH | `/api/tasks/{task_id}` | защищённый | частичное изменение задачи | 200 |
| DELETE | `/api/tasks/{task_id}` | защищённый | удаление задачи | 204 |

## Авторизация

Серверная модель сессий с одним случайным access-токеном (32 случайных байта,
энтропия 256 бит; в БД хранится только SHA-256 хеш). Сессия действует 24 часа.
Токен передаётся двумя независимыми способами:

- `Authorization: Bearer <access_token>` — можно вставить через кнопку
  Authorize в Swagger UI;
- Cookie `access_token=<access_token>` (HttpOnly, SameSite=Lax, Path=/,
  срок 24 часа) — устанавливается автоматически при входе.

Правила приоритета: если переданы оба способа — используется заголовок
Authorization; если заголовок присутствует, но некорректен, — 401 без перехода
к Cookie. Любая ошибка авторизации — 401 с заголовком
`WWW-Authenticate: Bearer`. Выход удаляет только текущую сессию и очищает
Cookie; другие сессии пользователя продолжают работать.

## База данных

Три таблицы: `users`, `auth_sessions`, `tasks`. Внешние ключи реально
контролируются SQLite (`PRAGMA foreign_keys=ON`). Статусы задачи
(`pending`, `in_progress`, `completed`) и приоритеты (`low`, `medium`, `high`)
ограничены ограничениями CHECK на уровне БД. Время в API — ISO 8601 в UTC
(суффикс `Z`), дата срока — `YYYY-MM-DD`.

## Проверка работоспособности

После запуска сервера выполните в отдельном терминале:

```bash
python smoke_test.py               # сценарии 1-14, 16, 17 из ТЗ
# остановите сервер (Ctrl+C), запустите снова и выполните:
python smoke_test.py --after-restart   # сценарий 15 из ТЗ
```

Скрипт печатает PASS/FAIL по каждому сценарию и итоговый результат.

## Примеры запросов

```bash
# Регистрация
curl -X POST http://127.0.0.1:8000/api/users/register \
  -H "Content-Type: application/json" \
  -d '{"username": "student01", "password": "secret123"}'

# Вход (токен вернётся в JSON и в Cookie)
curl -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "student01", "password": "secret123"}'

# Создание задачи через Bearer
curl -X POST http://127.0.0.1:8000/api/tasks \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json" \
  -d '{"title": "Подготовить отчёт", "priority": "high", "due_date": "2026-12-01"}'

# Список с фильтрами, поиском и пагинацией
curl "http://127.0.0.1:8000/api/tasks?status=pending&priority=high&search=отчёт&limit=10&offset=0" \
  -H "Authorization: Bearer <access_token>"

# Выход
curl -X POST http://127.0.0.1:8000/api/auth/logout \
  -H "Authorization: Bearer <access_token>"
```

## Принятые ограничения

Разрабатывается только backend: графический интерфейс, административная панель,
совместное редактирование, уведомления, восстановление пароля, вход через
сторонние сервисы и развёртывание на сервере не входят в объём. Приложение
предназначено для локального использования: защита от перебора паролей,
CSRF-защита и ротация токенов не реализуются. JWT, refresh-токены, роли и
миграции Alembic не используются.
