# IAP – Calendar Sync Backend

A FastAPI backend with fully integrated two-way Google Calendar synchronization.

## Features

- **Google OAuth 2.0** – Secure user authentication
- **Two-Way Sync** – Bidirectional sync between app and Google Calendar
- **Webhook Push Notifications** – Real-time updates from Google Calendar
- **Background Jobs** – Auto webhook renewal + periodic fallback sync
- **Fixed Slots CRUD** – Create/update/delete time slots that sync to Google
- **Loop Prevention** – Circuit breaker prevents infinite sync loops

## Quick Start

```bash
# 1. Create virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your Google OAuth credentials

# 4. Start the server
uvicorn main:app --reload
```

API docs at **http://localhost:8000/docs**

## Google Cloud Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a project → Enable **Google Calendar API**
3. Create **OAuth 2.0 credentials** (Web application)
4. Add redirect URI: `http://localhost:8000/auth/google/callback`
5. Copy Client ID + Secret into `.env`

## Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | DB connection string (default: SQLite) |
| `GOOGLE_CLIENT_ID` | Google OAuth Client ID |
| `GOOGLE_CLIENT_SECRET` | Google OAuth Client Secret |
| `OAUTH_REDIRECT_URI` | OAuth callback URL |
| `WEBHOOK_BASE_URL` | Public URL for Google push notifications (use ngrok locally) |
| `SECRET_KEY` | App secret key |

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/auth/users` | Create a user |
| `GET` | `/auth/google/authorize` | Get Google OAuth URL |
| `GET` | `/auth/google/callback` | OAuth callback (auto-inits sync) |
| `POST` | `/auth/initialize/{user_id}` | Manually init calendar sync |
| `GET` | `/auth/users` | List all users |

### Slots (synced to Google Calendar)
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/slots` | Create slot → pushes to Google |
| `GET` | `/slots` | List user's slots |
| `PUT` | `/slots/{id}` | Update slot → pushes to Google |
| `DELETE` | `/slots/{id}` | Soft-delete → deletes from Google |

### Sync Management
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/sync/trigger` | Manual pull from Google |
| `GET` | `/sync/status` | Check sync state + webhook info |
| `POST` | `/sync/push-all` | Push all un-synced slots to Google |

### Webhooks
| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/webhooks/google-calendar` | Receive Google push notifications |
| `POST` | `/webhooks/setup/{user_id}` | Set up webhook channel |

## Project Structure

```
IAP---backend/
├── main.py                     # FastAPI app + startup/shutdown
├── requirements.txt
├── .env.example
├── alembic.ini
├── alembic/                    # DB migrations
│   ├── env.py
│   └── versions/
├── api/                        # Route handlers
│   ├── auth.py                 # OAuth + user management
│   ├── slots.py                # Slot CRUD → Google sync
│   ├── sync.py                 # Manual sync + status
│   └── webhooks.py             # Google push notifications
├── persistence/                # Database layer
│   ├── database.py
│   ├── models.py               # User, FixedSlot, CalendarSyncState
│   └── repositories/
│       ├── user_repository.py
│       ├── fixed_slot_repository.py
│       └── sync_state_repository.py
├── services/                   # Business logic
│   ├── google_oauth.py         # OAuth token management
│   ├── calendar_service.py     # Google Calendar API calls
│   └── sync_engine.py          # Two-way sync with loop prevention
├── schemas/
│   └── slot_schemas.py         # Pydantic request/response models
└── background/
    └── scheduler.py            # Webhook renewal + periodic sync
```

## Usage Flow

1. **Create user** → `POST /auth/users`
2. **Authorize with Google** → open URL from `GET /auth/google/authorize`
3. **OAuth callback** auto-creates sync state, initial sync, and webhook
4. **CRUD slots** → automatically sync to/from Google Calendar
5. **Background scheduler** handles webhook renewal and periodic sync

## License

MIT
