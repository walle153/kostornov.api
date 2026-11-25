#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Автопроверка 17 сценариев приёмки из ТЗ «Менеджер управления задачами».

Запуск при работающем сервере (uvicorn app.main:app --reload):
    python smoke_test.py                 # сценарии 1-14, 16, 17
    python smoke_test.py --after-restart # сценарий 15 после перезапуска

Скрипт использует только стандартную библиотеку.
"""

import hashlib
import json
import secrets
import sqlite3
import sys
import urllib.error
import urllib.request
from urllib.parse import quote

BASE_URL = "http://127.0.0.1:8000"
DB_FILE = "taskbox.db"
STATE_FILE = "restart_state.json"

SALT = secrets.token_hex(4)
USER_A = f"tester_{SALT}_a"
USER_B = f"tester_{SALT}_b"
PASSWORD = "correct-horse-42"

results = []
failures = []


def check(number, name, ok, note=""):
    mark = "PASS" if ok else "FAIL"
    results.append(number)
    if not ok:
        failures.append(number)
    print(f"[{mark}] Сценарий {number}: {name}" + (f" — {note}" if note else ""))


def request(method, path, token=None, use_cookie=False, raw_header=None, body=None, query=None):
    url = BASE_URL + path
    if query:
        url += "?" + "&".join(f"{k}={quote(str(v))}" for k, v in query.items())
    payload = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=payload, method=method)
    if payload is not None:
        req.add_header("Content-Type", "application/json")
    if raw_header:
        req.add_header("Authorization", raw_header)
    elif token:
        if use_cookie:
            req.add_header("Cookie", f"access_token={token}")
        else:
            req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req) as resp:
            return resp.status, resp.read().decode("utf-8"), dict(resp.headers)
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8"), dict(exc.headers)


def parse(text):
    try:
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return {}


def main():
    # --- Сценарий 1: первый запуск, health ---
    status, text, _ = request("GET", "/api/health")
    check(1, "Первый запуск без файла БД", status == 200 and parse(text).get("status") == "ok",
          f"GET /api/health -> {status}")

    # --- Сценарий 2: регистрация двух пользователей ---
    status_a, text_a, _ = request("POST", "/api/users/register",
                                  body={"username": USER_A, "password": PASSWORD})
    status_b, text_b, _ = request("POST", "/api/users/register",
                                  body={"username": USER_B, "password": PASSWORD})
    user_a, user_b = parse(text_a), parse(text_b)
    check(2, "Регистрация двух разных пользователей",
          status_a == 201 and status_b == 201 and user_a.get("id") != user_b.get("id"),
          f"{status_a}, {status_b}")

    # Проверка: в БД только хеш пароля
    conn = sqlite3.connect(DB_FILE)
    stored = conn.execute("SELECT password_hash FROM users WHERE username = ?", (USER_A,)).fetchone()
    conn.close()
    hash_ok = bool(stored) and isinstance(stored[0], str) and PASSWORD not in stored[0] and stored[0].startswith("$")
    if not hash_ok:
        check(2, "Регистрация: в БД только хеш пароля", False, f"stored={stored and stored[0][:20]!r}")

    # --- Сценарий 3: повторная регистрация ---
    status, text, _ = request("POST", "/api/users/register",
                              body={"username": USER_A, "password": PASSWORD})
    check(3, "Повторная регистрация занятого имени", status == 409 and "detail" in parse(text),
          f"{status} {parse(text).get('detail', '')}")

    # --- Сценарий 4: неверный пароль и неизвестное имя ---
    s1, _, _ = request("POST", "/api/auth/login", body={"username": USER_A, "password": "wrong-pass-99"})
    s2, _, _ = request("POST", "/api/auth/login", body={"username": "nobody_x999", "password": PASSWORD})
    check(4, "Неверный пароль / неизвестное имя -> 401", s1 == 401 and s2 == 401, f"{s1}, {s2}")

    # --- Сценарий 5: корректный вход ---
    status, text, headers = request("POST", "/api/auth/login", body={"username": USER_A, "password": PASSWORD})
    login_data = parse(text)
    token_a = login_data.get("access_token", "")
    set_cookie = headers.get("Set-Cookie", "")
    check(5, "Корректный вход",
          status == 200 and token_a and login_data.get("token_type") == "bearer"
          and login_data.get("expires_in") == 86400 and "access_token=" in set_cookie
          and "HttpOnly" in set_cookie and "SameSite=lax" in set_cookie,
          f"{status}")

    # --- Сценарий 6: профиль через Bearer и через Cookie ---
    s_b, t_b, _ = request("GET", "/api/users/me", token=token_a, use_cookie=True)
    s_h, t_h, _ = request("GET", "/api/users/me", token=token_a)
    same = parse(t_b) == parse(t_h) and parse(t_h).get("username") == USER_A
    check(6, "Профиль: Bearer и Cookie", s_b == 200 and s_h == 200 and same, f"{s_b}, {s_h}")

    # --- Сценарий 7: без токена, битый токен, неверный Bearer + Cookie ---
    s_none, _, _ = request("GET", "/api/users/me")
    s_bad, _, _ = request("GET", "/api/users/me", token="not-a-real-token-123")
    www = None
    s_mixed, _, headers_mixed = request("GET", "/api/users/me",
                                        token=token_a, use_cookie=True, raw_header="Bearer garbage")
    www = headers_mixed.get("WWW-Authenticate", "")
    check(7, "401 без токена / битый токен / неверный Bearer",
          s_none == 401 and s_bad == 401 and s_mixed == 401 and "Bearer" in www,
          f"{s_none}, {s_bad}, {s_mixed}; WWW-Authenticate: {www!r}")

    # --- Сценарий 8: смена имени ---
    s_same, _, _ = request("PATCH", "/api/users/me", token=token_a, body={"username": USER_A})
    new_name = f"renamed_{SALT}"
    s_ok, t_ok, _ = request("PATCH", "/api/users/me", token=token_a, body={"username": new_name})
    s_conf, _, _ = request("PATCH", "/api/users/me", token=token_a, body={"username": USER_B})
    check(8, "Смена имени", s_same == 200 and s_ok == 200 and parse(t_ok).get("username") == new_name
          and s_conf == 409, f"same={s_same}, ok={s_ok}, conflict={s_conf}")

    # --- Сценарий 9: создание задачи только с title ---
    status, text, _ = request("POST", "/api/tasks", token=token_a, body={"title": "Первая задача"})
    task1 = parse(text)
    check(9, "Создание задачи только с title",
          status == 201 and task1.get("user_id") == parse(t_h if s_ok != 200 else t_ok).get("id")
          and task1.get("status") == "pending" and task1.get("priority") == "medium"
          and task1.get("due_date") is None and task1.get("created_at", "").endswith("Z"),
          f"{status}")

    # --- Сценарий 10: частичное редактирование ---
    status, text, _ = request("PATCH", f"/api/tasks/{task1['id']}", token=token_a,
                              body={"status": "in_progress", "description": None})
    updated = parse(text)
    check(10, "Частичное редактирование задачи",
          status == 200 and updated.get("status") == "in_progress"
          and updated.get("description") is None
          and updated.get("priority") == "medium" and updated.get("title") == task1["title"]
          and updated.get("updated_at") != task1["updated_at"],
          f"{status}")

    # --- Сценарий 11: список, фильтры, поиск, пагинация ---
    for i, (title, st, pr) in enumerate([
        ("Buy milk", "pending", "low"),
        ("Write report", "in_progress", "high"),
        ("Read book", "completed", "medium"),
        ("Write letter", "pending", "high"),
    ]):
        request("POST", "/api/tasks", token=token_a, body={"title": title, "status": st, "priority": pr})
    request("POST", "/api/tasks", token=token_b, body={"title": "Task of user B"})

    s_all, t_all, _ = request("GET", "/api/tasks", token=token_a)
    all_data = parse(t_all)
    s_f, t_f, _ = request("GET", "/api/tasks", token=token_a,
                          query={"status": "pending", "priority": "high"})
    f_data = parse(t_f)
    s_s, t_s, _ = request("GET", "/api/tasks", token=token_a, query={"search": "write"})
    s_data = parse(t_s)
    s_p, t_p, _ = request("GET", "/api/tasks", token=token_a, query={"limit": 2, "offset": 2})
    p_data = parse(t_p)
    only_owner = all(item.get("user_id") == task1.get("user_id") for item in all_data.get("items", []))
    ids = [item["id"] for item in p_data.get("items", [])]
    check(11, "Список, фильтры, поиск, пагинация",
          s_all == 200 and all_data.get("total") == 5 and len(all_data.get("items", [])) == 5
          and only_owner
          and s_f == 200 and f_data.get("total") == 1 and f_data["items"][0]["title"] == "Write letter"
          and s_s == 200 and s_data.get("total") == 2
          and s_p == 200 and p_data.get("total") == 5 and len(p_data.get("items", [])) == 2
          and ids == sorted(ids, reverse=True),
          f"all={all_data.get('total')}, f={f_data.get('total')}, s={s_data.get('total')}, p={p_data.get('limit')}")

    # --- Сценарий 12: изоляция данных ---
    s_g, _, _ = request("GET", f"/api/tasks/{task1['id']}", token=token_b)
    s_p2, _, _ = request("PATCH", f"/api/tasks/{task1['id']}", token=token_b, body={"title": "hack"})
    s_d, _, _ = request("DELETE", f"/api/tasks/{task1['id']}", token=token_b)
    s_after, t_after, _ = request("GET", f"/api/tasks/{task1['id']}", token=token_a)
    untouched = parse(t_after).get("title") == task1["title"]
    check(12, "Чужая задача: GET/PATCH/DELETE -> 404",
          s_g == 404 and s_p2 == 404 and s_d == 404 and untouched and s_after == 200,
          f"{s_g}, {s_p2}, {s_d}")

    # --- Сценарий 13: невалидные значения ---
    s_e1, _, _ = request("POST", "/api/tasks", token=token_a, body={"title": "x", "status": "nope"})
    s_e2, _, _ = request("POST", "/api/tasks", token=token_a, body={"title": "y", "priority": "urgent"})
    s_e3, _, _ = request("POST", "/api/tasks", token=token_a, body={"title": "  "})
    s_e4, _, _ = request("PATCH", f"/api/tasks/{task1['id']}", token=token_a, body={})
    s_e5, _, _ = request("POST", "/api/tasks", token=token_a,
                         body={"title": "z", "user_id": 999, "id": 777})
    s_e6, _, _ = request("GET", "/api/tasks", token=token_a, query={"limit": 500})
    check(13, "Невалидные значения, пустой PATCH, чужой user_id",
          s_e1 == 422 and s_e2 == 422 and s_e3 == 422 and s_e4 == 422 and s_e5 == 422 and s_e6 == 422,
          f"{s_e1}, {s_e2}, {s_e3}, {s_e4}, {s_e5}, {s_e6}")

    # --- Сценарий 14: удаление и повторный запрос ---
    s_del, _, headers = request("DELETE", f"/api/tasks/{task1['id']}", token=token_a)
    s_again, _, _ = request("GET", f"/api/tasks/{task1['id']}", token=token_a)
    no_body = True
    check(14, "Удаление задачи, затем 404", s_del == 204 and s_again == 404, f"{s_del}, {s_again}")

    # --- Сценарий 16: две сессии, выход из одной ---
    _, text_1, _ = request("POST", "/api/auth/login", body={"username": USER_A, "password": PASSWORD})
    token_a2 = parse(text_1)["access_token"]
    _, _, _ = request("POST", "/api/auth/login", body={"username": USER_A, "password": PASSWORD})
    s_out, _, _ = request("POST", "/api/auth/logout", token=token_a2)
    s_rev_b, _, _ = request("GET", "/api/users/me", token=token_a2, use_cookie=True)
    s_rev_h, _, _ = request("GET", "/api/users/me", token=token_a2)
    s_other, _, _ = request("GET", "/api/users/me", token=token_a)
    check(16, "Выход из одной сессии, вторая жива",
          s_out == 204 and s_rev_b == 401 and s_rev_h == 401 and s_other == 200,
          f"logout={s_out}, revoked={s_rev_b}/{s_rev_h}, other={s_other}")

    # --- Сценарий 17: документация ---
    s_docs, _, _ = request("GET", "/docs")
    s_open, t_open, _ = request("GET", "/openapi.json")
    schema = parse(t_open) if s_open == 200 else {}
    paths = schema.get("paths", {})
    routes = sum(len(paths.get(p, {})) for p in paths)
    has_schemes = "BearerSession" in t_open and "CookieSession" in t_open
    check(17, "Swagger UI и OpenAPI описывают все маршруты и оба способа авторизации",
          s_docs == 200 and routes >= 11 and has_schemes, f"docs={s_docs}, routes={routes}")

    print()
    print(f"Итого: {len(results) - len(failures)}/{len(results)} сценариев прошли.")
    if failures:
        print(f"Провалены сценарии: {', '.join(map(str, sorted(failures)))}")
    else:
        print("Все проверенные сценарии приёмки пройдены.")

    # Сохраняем состояние для сценария 15
    state = {"username": USER_A, "password": PASSWORD, "token": token_a,
             "remaining_task_id": None}
    s_last, t_last, _ = request("GET", "/api/tasks", token=token_a, query={"limit": 1})
    items = parse(t_last).get("items", [])
    if items:
        state["remaining_task_id"] = items[0]["id"]
        state["task_title"] = items[0]["title"]
    with open(STATE_FILE, "w", encoding="utf-8") as fh:
        json.dump(state, fh)
    print(f"\nДля сценария 15: перезапустите сервер (Ctrl+C, затем uvicorn app.main:app --reload), "
          f"затем выполните: python smoke_test.py --after-restart")


def after_restart():
    """Сценарий 15: пользователи, задачи и неистёкшие сессии пережили перезапуск."""
    try:
        state = json.load(open(STATE_FILE, encoding="utf-8"))
    except FileNotFoundError:
        print("Файл restart_state.json не найден. Сначала выполните python smoke_test.py.")
        sys.exit(1)

    token = state["token"]
    s_profile, t_profile, _ = request("GET", "/api/users/me", token=token, use_cookie=True)
    profile_ok = s_profile == 200 and parse(t_profile).get("username") == state["username"]

    s_task, t_task, _ = request("GET", f"/api/tasks/{state['remaining_task_id']}", token=token)
    task_ok = s_task == 200 and parse(t_task).get("title") == state["task_title"]

    # Истёкшая сессия: создаём новую и «старим» её прямо в БД
    _, t_login, _ = request("POST", "/api/auth/login",
                            body={"username": state["username"], "password": state["password"]})
    expired_token = parse(t_login).get("access_token", "")
    token_hash = hashlib.sha256(expired_token.encode("utf-8")).hexdigest()
    conn = sqlite3.connect(DB_FILE)
    conn.execute("UPDATE auth_sessions SET expires_at = '2020-01-01 00:00:00' WHERE token_hash = ?",
                 (token_hash,))
    conn.commit()
    conn.close()
    s_expired, _, headers_exp = request("GET", "/api/users/me", token=expired_token)

    check(15, "Перезапуск: сессии и задачи сохранены",
          profile_ok and task_ok and s_expired == 401 and "Bearer" in headers_exp.get("WWW-Authenticate", ""),
          f"profile={s_profile}, task={s_task}, expired={s_expired}")

    if failures:
        print(f"Провалены сценарии: {', '.join(map(str, sorted(failures)))}")
        sys.exit(1)
    print("Сценарий 15 пройден: данные пережили перезапуск сервера.")


if __name__ == "__main__":
    if "--after-restart" in sys.argv:
        after_restart()
    else:
        main()
