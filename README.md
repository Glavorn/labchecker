# LabChecker

Сдача и автопроверка лаб (Python/Bash) для курса ДЕВАП: студент грузит файл или zip с решением, бэкенд гоняет линтер и сразу ставит статус, препод видит сводную таблицу по всем сдачам.

## Стек

- **FastAPI + SQLAlchemy** — REST API и ORM поверх БД, иначе каждый CRUD писать вручную на SQL.
- **PostgreSQL** — данные реляционные (сдача = FK на студента и лабу), нужны нормальные ключи и enum под статусы.
- **flake8 / shellcheck** — это и есть сама проверка, а не обвязка вокруг неё.
- **Nginx** — одна точка входа: отдаёт фронт, проксирует `/api`, не нужен CORS.
- **Docker Compose** — поднимает db → backend → nginx одной командой.

## Запуск

```bash
git clone <repo> && cd labchecker
docker compose up --build -d
```

Порт `8080`.

## Как пользоваться

Студентов и лабы добавляет препод формами в интерфейсе. Студент выбирает себя и лабу, кидает `.py`/`.sh` или zip проекта — статус появляется сразу после проверки. Если линтер неправ, статус меняется руками через `PATCH /api/submissions/{id}`.

## Структура

```
backend/app/
  routers/    — students, labs, submissions — сами эндпоинты
  services/   — checker.py: запуск flake8/shellcheck по файлу или по zip
  models.py   — Student, Lab, Submission

frontend/
  js/         — по модулю на сущность (students, labs, submissions) + api.js
```
