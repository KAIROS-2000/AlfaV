# Progyx Fullsite v3

Полноценный fullstack‑сайт для обучения программированию по методичке Progyx и вашим уточнениям по ролям.

## Что реализовано

- регистрация и вход через backend-set `HttpOnly` session cookies
- роли: `student`, `teacher`, `admin`, `superadmin`
- **суперадмин** (роль `superadmin`): при `SUPERADMIN_BOOTSTRAP=true` и заданных `SUPERADMIN_EMAIL` / `SUPERADMIN_PASSWORD` учётка создаётся при `flask bootstrap-app` (в шаблоне `.env.example` для локалки задано по умолчанию; это не то же, что демо-админ из `DEMO_ADMIN_*` ниже)
- ученик: dashboard, roadmap, уроки, теория, практика, мини‑тесты, достижения, рейтинг, вступление в класс
- teacher workflow: создание классов, назначение заданий, просмотр учеников, проверка сдач
- teacher practice builder: ручная проверка, авто‑проверка по ключевым словам и настоящие автотесты для `Python`/`JavaScript`
- админ: просмотр пользователей, создание модулей, публикация и снятие с публикации
- суперадмин: создание, блокировка, разблокировка и удаление обычных админов
- родительский кабинет по семейной ссылке-приглашению
- смешанные тесты: single choice, multiple choice, ordering, matching
- красивый roadmap в стиле path‑based learning: крупные пунсоны-узлы соединены линией, состояния уроков видны визуально
- Docker Compose для фронтенда, бэкенда, PostgreSQL и изолированного `judge-runner`

## Руководства по ролям

Для повседневной работы используйте отдельные инструкции: [суперадминистратор](docs/user-guides/superadmin.md), [администратор](docs/user-guides/admin.md), [учитель](docs/user-guides/teacher.md) и [менеджер](docs/user-guides/manager.md). Общая страница со ссылками находится в [docs/user-guides](docs/user-guides/README.md).

## Актуальный стек

- Backend: Flask + Flask-SQLAlchemy + PostgreSQL + PyJWT + Gunicorn
- Frontend: Next.js + React + Tailwind CSS + GSAP
- Учебные инструменты: Monaco Editor, текстовые и кодовые практики

## Быстрый старт

```bash

cp .env.example .env

sh scripts/generate-secrets.sh ./secrets
docker compose -f compose.yml -f compose.dev.yml up --build
```

После запуска:

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000/api
- **Суперадмин:** логин `superadmin@codequest.local` или `superadmin`, пароль — значение `SUPERADMIN_PASSWORD` в `.env` (в `.env.example` для локалки: `LocalOnlySuperAdmin123!`). Учётка появляется только при `SUPERADMIN_BOOTSTRAP=true` и успешном `bootstrap-app`; роль `admin` из блока `DEMO_ADMIN_*` — это отдельный демо-пользователь.
- browser API calls use the portable same-origin `NEXT_PUBLIC_API_URL=/api`; no API hostname is baked into the image
- server-side proxy фронтенда ходит в backend через `INTERNAL_API_URL`
- `judge-runner` поднимается внутри Docker-сети и не публикует порт наружу

## Development and production

Development uses source bind mounts, Flask reload, `next dev`, and named
`node_modules`/`.next` volumes, so normal React/Python edits need no rebuild.

```bash
docker compose -f compose.yml -f compose.dev.yml up --build
docker compose -f compose.yml -f compose.dev.yml --profile backup up -d
```

Production runs only prebuilt, signed `@sha256:` image digests (no source
bind mounts), terminates TLS through Caddy, enables local plus encrypted
off-host backups, and uses named media/audit volumes. Production never reuses
the development `.env`:

```bash
cp .env.production.example /secure/path/progyx-production.env
# Replace every placeholder and point *_FILE_HOST variables at external secret files.
sh scripts/production-preflight.sh /secure/path/progyx-production.env
docker compose --env-file /secure/path/progyx-production.env -f compose.yml -f compose.prod.yml pull
docker compose --env-file /secure/path/progyx-production.env -f compose.yml -f compose.prod.yml up -d --wait --no-build
```

The full production procedure, evidence checklist, first Restic initialization,
and rollback rules are documented in
[`docs/operations/production-release.md`](docs/operations/production-release.md).
Monitoring signals, SLOs and the mandatory alert-route test are in
[`docs/operations/observability.md`](docs/operations/observability.md).

Backup/restore commands (restore is destructive):

```bash
docker compose --env-file /secure/path/progyx-production.env -f compose.yml -f compose.prod.yml run --rm --entrypoint sh db-backup /usr/local/bin/backup.sh
docker compose --env-file /secure/path/progyx-production.env -f compose.yml -f compose.prod.yml exec -e RESTORE_ASSUME_YES=1 db-backup sh /usr/local/bin/restore.sh /backups/<file>.sql.custom.gz
```

## Production режим

- для локального старта используйте `APP_ENV=development`
- для frontend также выставляйте `NEXT_PUBLIC_APP_ENV=development`
- при `APP_ENV=production`:
  - `PUBLIC_ORIGIN`, `CLIENT_URL` и runtime-only `INTERNAL_API_URL` должны приходить из env
  - `ENABLE_DEMO_DATA=false`
  - `SUPERADMIN_BOOTSTRAP=false`; первый администратор создаётся отдельной аудируемой CLI-командой из production runbook
- frontend is built once with `next build` and runs the standalone `node server.js` runtime
- backend запускается через Gunicorn, а `flask.run()` запрещён в production
- если в `APP_ENV=production` оставлен слабый `SECRET_KEY` (`dev-secret-key` или `super-secret-key-change-me`), backend завершит запуск с ошибкой
- в `APP_ENV=production` обязательны `SESSION_COOKIE_SECURE=true`, полная email/legal-конфигурация и закрытые release-attestation gates
- GigaChat endpoint жёстко отключён и его credentials не загружаются приложением

## Email-уведомления

Backend отправляет транзакционные письма через общий email-сервис:

- подтверждение email и сброс пароля
- уведомления админам и учителям
- письма ученикам о новых уроках/заданиях от учителя
- письма родителям о достижениях ребёнка
- еженедельное письмо родителю с прямой ссылкой на прогресс ребёнка

Основные настройки:

```env
SEND_MAIL=true
SEND_NOTIFICATION_EMAILS=true
EMAIL_DRY_RUN=false
MESSAGE_NOTIFICATION_EMAIL_COOLDOWN_MINUTES=15
```

Для еженедельной родительской рассылки в production предпочтительно использовать внешний cron/scheduler, а не in-process thread backend-а:

```bash
flask --app backend/app send-weekly-parent-progress-emails
```

Причина: в production backend часто запускается в нескольких воркерах или контейнерах. Если планировщик живёт внутри web-процесса, каждый воркер может попытаться выполнить рассылку, а при рестарте приложения задача может быть пропущена. Внешний cron, Docker cron, Kubernetes CronJob, Celery beat или аналог даёт один контролируемый запуск, понятные логи и безопасный ручной повтор. In-process runner оставлен как опция и по умолчанию выключен через `ENABLE_PARENT_WEEKLY_PROGRESS_EMAIL_THREAD=false`.

## Автопроверка кода

- в конструкторе teacher-урока для практики можно выбрать:
- `Ручная проверка`
- `Авто по ориентирам` для текстовых ответов
- `Автотесты` для консольных задач на `Python` и `JavaScript`
- режим `Автотесты` ожидает программу, которая читает из `stdin` и пишет результат в `stdout`
- в `docker compose` backend отправляет код в отдельный сервис `judge-runner`
- runner запускает код в собственной временной директории, с таймаутом, лимитом памяти и сокращённым окружением
- локальный fallback по умолчанию отключён и должен включаться только в доверенной локальной среде

Поддерживаемые настройки `.env`:

```env
NEXT_PUBLIC_APP_ENV=development
NEXT_PUBLIC_API_URL=http://localhost:3000/api
INTERNAL_API_URL=http://localhost:8000/api
CLIENT_URL=http://localhost:3000
CODE_JUDGE_PYTHON_BIN=python
CODE_JUDGE_NODE_BIN=node
CODE_JUDGE_RUNNER_URL=http://localhost:8090/execute
CODE_JUDGE_DEFAULT_TIME_LIMIT_MS=2000
CODE_JUDGE_DEFAULT_MEMORY_LIMIT_MB=128
CODE_JUDGE_MAX_OUTPUT_CHARS=4000
CODE_JUDGE_RUNNER_TIMEOUT_MS=15000
CODE_JUDGE_ALLOW_LOCAL_FALLBACK=false
```

## Тестовые данные (только для локальной проверки)

Если нужно поднять демо-аккаунты и тестовые сценарии, добавьте в `.env`:

```env
ENABLE_DEMO_DATA=true
DEMO_STUDENT_EMAIL=student@codequest.local
DEMO_STUDENT_PASSWORD=Student123!
DEMO_TEACHER_EMAIL=teacher@codequest.local
DEMO_TEACHER_PASSWORD=Teacher123!
DEMO_ADMIN_EMAIL=admin@codequest.local
DEMO_ADMIN_PASSWORD=Admin123!
DEMO_CLASS_CODE=CLASS5B
DEMO_PARENT_CODE=PAR-DEMO2026
```

Тогда будут доступны сценарии:

- вход под тестовыми пользователями выше
- вступление ученика в класс по коду `CLASS5B`
- родительский кабинет по адресу `/parent/PAR-DEMO2026`

## Структура

```text
backend/
  app/
    api/        # auth, student, teacher, admin
    core/       # config, db, security, gamification
    models/     # users, modules, lessons, assignments, invites, progress
    seed/       # учебный контент и опциональный bootstrap суперадмина
frontend/
  src/app/      # страницы App Router
  src/components/
  src/lib/
```

## Ключевые маршруты API

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/refresh`
- `GET /api/dashboard`
- `GET /api/modules`
- `GET /api/lessons/<id>`
- `POST /api/tasks/<id>/submit`
- `POST /api/quizzes/<id>/submit`
- `POST /api/classes/join`
- `POST /api/parent/invite`
- `GET /api/parent/access/<code>`
- `GET /api/teacher/classes`
- `POST /api/teacher/classes/<id>/assignments`
- `PATCH /api/teacher/submissions/<id>/grade`
- `GET /api/admin/overview`
- `POST /api/admin/admins`
- `PATCH /api/admin/admins/<id>/block`
- `DELETE /api/admin/admins/<id>`

## Что можно доработать дальше

- более умная проверка текстовых ответов
- песочница исполнения Python/JS в Web Worker
- отдельный профиль‑редактор с аватарами и dark mode
- звуки, confetti, daily chest, weekly leaderboard reset
- миграции Alembic и e2e‑тесты
