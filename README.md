# Intelligent Academic Planner — Backend

A unified **FastAPI** backend merging two systems:

- **System A** — Academic planner with JWT auth, user management, courses, tasks (with collision detection), and onboarding.
- **System B** — Google Calendar two-way sync, OAuth integration, webhook-based real-time updates, and background sync scheduler.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI (async) |
| ORM | SQLAlchemy 2.0 (async) |
| Database | PostgreSQL + asyncpg |
| Migrations | Alembic (async) |
| Auth | JWT (python-jose) + bcrypt |
| Google Integration | google-api-python-client, google-auth-oauthlib |
| Background Jobs | APScheduler (AsyncIOScheduler) |
| Validation | Pydantic v2 |

---

## API Routes (33 endpoints)

| Group | Endpoints |
|---|---|
| **Auth** | `POST /login/access-token`, `GET /google/authorize`, `GET /google/callback` |
| **Users** | `POST /users/`, `GET /users/me`, `PUT /users/me/profile`, `POST /users/me/password`, `POST /users/password-recovery/{email}`, `POST /users/reset-password/` |
| **Admin** | `GET /admin/users` |
| **Onboarding** | `GET /onboarding/status`, `POST /onboarding/questionnaire` |
| **Courses** | `GET /courses/`, `POST /courses/`, `PATCH /courses/{id}`, `DELETE /courses/{id}` |
| **Tasks** | `GET /tasks/`, `POST /tasks/`, `PATCH /tasks/{id}`, `DELETE /tasks/{id}` |
| **Schedule** | `GET /schedule/fixed`, `POST /schedule/fixed`, `POST /schedule/slots`, `PUT /schedule/slots/{id}`, `DELETE /schedule/slots/{id}` |
| **Sync** | `POST /sync/trigger`, `POST /sync/reset`, `GET /sync/status`, `POST /sync/push-all`, `POST /sync/initialize` |
| **Webhooks** | `POST /webhooks/google-calendar`, `POST /webhooks/setup` |

All routes are prefixed with `/api/v1`. Interactive docs at `http://localhost:8000/docs`.

---

## Project Structure

```
iap-backend/
├── app/
│   ├── main.py                 # FastAPI entrypoint + lifespan
│   ├── api/
│   │   ├── deps.py             # DB session, JWT auth dependencies
│   │   └── v1/                 # Route handlers (auth, users, admin, etc.)
│   ├── core/
│   │   ├── config.py           # Pydantic Settings (.env loader)
│   │   ├── security.py         # Password hashing, JWT creation
│   │   └── utils.py            # Password reset token helpers
│   ├── db/
│   │   ├── base.py             # SQLAlchemy DeclarativeBase
│   │   └── session.py          # Async engine + session factory
│   ├── models/                 # SQLAlchemy ORM models
│   ├── schemas/                # Pydantic request/response schemas
│   ├── services/               # Google OAuth, Calendar API, Sync engine
│   └── background/
│       └── scheduler.py        # APScheduler (webhook renewal, periodic sync)
├── alembic/                    # Database migrations
├── .env.example                # Environment variable template
├── alembic.ini
├── requirements.txt
└── README.md
```

---

## Quick Start

### Prerequisites

- **Python 3.11+**
- **PostgreSQL** running locally (default: `localhost:5432`)

### 1. Clone & set up environment

```bash
git clone <repo-url>
cd iap-backend
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your database credentials, secret key, and Google OAuth keys
```

Key variables:

| Variable | Description |
|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://user:password@localhost:5432/iap_db` |
| `SECRET_KEY` | Random string for JWT signing |
| `GOOGLE_CLIENT_ID` | From Google Cloud Console |
| `GOOGLE_CLIENT_SECRET` | From Google Cloud Console |
| `WEBHOOK_BASE_URL` | Public HTTPS URL (e.g. ngrok) for Google Calendar webhooks |

### 3. Create the database

```sql
CREATE DATABASE iap_db;
```

### 4. Run migrations

```bash
# Windows PowerShell
$env:PYTHONPATH = "."
alembic upgrade head

# macOS/Linux
PYTHONPATH=. alembic upgrade head
```

### 5. Start the server

```bash
uvicorn app.main:app --reload --port 8000
```

Visit **http://localhost:8000/docs** for the Swagger UI.

---

## Google Calendar Integration

1. Register → Login → get JWT token
2. `GET /api/v1/google/authorize` (with Bearer token) → opens Google consent
3. Google redirects to `/api/v1/google/callback` → refresh token stored, sync initialized
4. Slots created via `/api/v1/schedule/slots` auto-push to Google Calendar
5. Changes in Google Calendar sync back via webhooks or `POST /api/v1/sync/trigger`

---

## License

This project is licensed under the MIT License — see [LICENSE](LICENSE) for details.
