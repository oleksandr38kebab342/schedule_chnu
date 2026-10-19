# Backend — система управління навчальним розкладом

FastAPI + PostgreSQL + Redis. Реалізовано весь бек MVP-1…MVP-6: довідники,
академічний календар, ядро розкладу, виявлення конфліктів з override та
аудитом, Redis-кешування, Excel-експорт. Для фронтенду (`../frontend`) додано
публічний роутер перегляду, сервіс представлення розкладу на дату та API
точкових змін (заміна, перенесення, скасування).

## Структура

```
backend/
  app/
    core/        config, database, security (bcrypt + JWT), довідник прав
    models/      SQLAlchemy 2.0, 35 таблиць (auth, organization, academic,
                 facilities, calendar, schedule, audit)
    schemas/     Pydantic-схеми запитів і відповідей
    services/    calendar (тижні+парність), conflicts, excel_export,
                 cache (Redis), audit, schedule_view (день/тиждень на дату)
    api/         deps (get_current_user, require_permission) + роути,
                 зокрема public (читання без входу) та audit
    main.py      FastAPI-застосунок + CORS
  alembic/       міграції (0001 auth+org, 0002 решта, 0003 заміни й перенесення)
  scripts/seed.py       права, 7 ролей, суперадміністратор
  scripts/seed_demo.py  демонстраційні довідники, розклад і користувачі
  tests/         100 pytest-тестів на SQLite, без Docker
```

## Запуск через Docker

```bash
cd ..                      # корінь репозиторію
docker compose up -d db cache
cp backend/.env.example backend/.env
cd backend
python -m alembic upgrade head
python -m scripts.seed
python -m scripts.seed_demo        # демо-дані для фронтенду (необовʼязково)
python -m uvicorn app.main:app --reload
```

Документація API: http://localhost:8000/docs (50 ендпоінтів). Повний стек разом
з API в контейнері: `docker compose up -d` з кореня.

## Локальне середовище

```bash
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt   # Windows
.venv/Scripts/python.exe -m pytest                            # 100 тестів, без Docker
```

## Основні групи ендпоінтів (усі під /api/v1)

| Група | Приклади | Право на запис |
|---|---|---|
| Авторизація | `POST /auth/login`, `GET /auth/me` | — |
| Факультети / кафедри | `/faculties`, `/departments` | `faculty.manage` / `department.manage` |
| Викладачі | `/teachers` (+ кафедри, сумісництво) | `teacher.manage` |
| Групи / підгрупи / потоки | `/groups`, `/groups/{id}/subgroups`, `/streams` | `group.manage` |
| Дисципліни / типи занять | `/subjects`, `/lesson-types` | `subject.manage` |
| Корпуси / аудиторії / пари | `/buildings`, `/rooms`, `/times` | `room.manage` |
| Календар | `/academic-years`, `/semesters`, `/semesters/{id}/generate-weeks`, `/week-for-date`, `/exceptions` | `calendar.manage` |
| Розклад | `POST /schedule`, `PUT /schedule/{id}`, `/schedule/group/{id}`, `/schedule/teacher/{id}`, `/schedule/room/{id}` | `schedule.create` / `schedule.edit` / `schedule.delete` |
| Точкові зміни | `POST /schedule/{id}/exceptions`, `DELETE /schedule/exceptions/{id}` | `schedule.move` / `schedule.cancel` / `schedule.edit` |
| Експорт | `POST /export` (.xlsx) | `schedule.export` |
| Журнал аудиту | `GET /audit` | `audit.view` |
| Публічний перегляд | `/public/groups`, `/public/calendar`, `/public/schedule/{group\|teacher\|room}/{id}/{day\|week}` | — (лише читання) |

## Ключова логіка (DoD ТЗ)

- **Календар** (`services/calendar.py`): тиждень рахується від `semester.start_date`,
  парність ODD/EVEN чергується, кожен семестр починає нумерацію з 1.
- **Конфлікти** (`services/conflicts.py`): збіг (семестр + день + пара + ресурс)
  з урахуванням парності — ODD+EVEN не конфліктують, BOTH конфліктує з усім.
  Викладач/аудиторія → ERROR, група/підгрупа → WARNING.
- **Override**: збереження попри ERROR-конфлікт лише з правом
  `schedule.override_conflict` і обовʼязковою причиною; усе пишеться в `audit_logs`.
- **Excel** (`services/excel_export.py`): дворядкова структура odd/even, обʼєднання
  однакових клітинок, накладки списком, Пн-Пт завжди / Сб-Нд за наявності занять,
  freeze_panes, друк Landscape. Сервіс не залежить від HTTP чи ORM.
- **Redis** (`services/cache.py`): кеш розкладу групи з інвалідацією при зміні
  заняття; якщо Redis недоступний — тихий fallback на БД.
- **Перегляд на дату** (`services/schedule_view.py`): шаблон «день+пара+парність»
  розгортається на конкретну дату з урахуванням календарних винятків і точкових
  змін; повертає готові для показу назви, а не ідентифікатори.
- **Публічний доступ**: роутер `/api/v1/public` лише читає і не вимагає входу;
  вимикається прапорцем `PUBLIC_SCHEDULE_ENABLED=false`.

## Пастки цього середовища

- **Кирилиця у шляху.** Docker Compose не виводить імʼя проєкту з папки
  «розклад», тому в `docker-compose.yml` задано `name: rozklad`.
- **Домени `.local`.** Валідатор email відкидає їх як зарезервовані — усюди
  використовується `chnu.edu.ua`.
- **Консоль cp1252.** Скрипти, що друкують кирилицю, перемикають stdout на UTF-8.
- **`JWT_SECRET`.** HS256 вимагає ключ від 32 байтів; дефолт лише для розробки.
- **Інтерпретатор у VS Code.** Вибрати `backend/.venv`, інакше залежності
  позначаються як невстановлені.
