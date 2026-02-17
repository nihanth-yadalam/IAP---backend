# L1 Intelligent Academic Planner — Backend API

<p align="center">
  <strong>A FastAPI backend that acts as a "Digital Twin" for students</strong><br>
  AI-powered academic scheduling with energy-based planning, Google Calendar sync, and behavioral analytics
</p>

---

## 📖 Project Overview

**L1: Intelligent Academic Planner** is a web-based productivity platform designed to solve the disconnect between planning and execution that students face daily. Unlike passive calendar applications that treat every hour as equal, L1 uses AI to model the user's habits, learning style, and energy levels to create realistic, achievable schedules.

### The Problem
Students face three critical planning challenges:
- **Optimism Bias**: Consistent underestimation of task durations
- **Mental Energy**: Standard calendars ignore human fatigue and burnout
- **Dynamic Chaos**: Missed deadlines make static calendars obsolete

### The Solution
L1 integrates academic context (deadlines, course difficulty) with behavioral health (burnout risk, procrastination patterns) to create a personalized, adaptive scheduling system that moves beyond "managing time" to **managing energy and focus**.

### Core Innovation
- **"Cold Start" Solution**: Initial profiling questionnaire establishes baseline user archetype
- **"Digital Twin" Memory**: Rolling "Reflexion" architecture learns user patterns over time
- **Energy-Based Scheduling**: Feedback loop records task drain to prevent burnout
- **Google Calendar Integration**: Seamless two-way sync with existing workflows

---

## 🛠️ Tech Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Framework** | FastAPI (async) | High-performance API with auto-generated docs |
| **ORM** | SQLAlchemy 2.0 (async) | Type-safe database interactions |
| **Database** | PostgreSQL + asyncpg | Relational data + JSONB for AI memory |
| **Migrations** | Alembic (async) | Schema versioning and updates |
| **Authentication** | JWT (python-jose) + bcrypt | Secure stateless sessions |
| **Google Integration** | google-api-python-client | OAuth2 + Calendar API |
| **Background Jobs** | APScheduler | Webhook renewal, periodic sync |
| **Validation** | Pydantic v2 | Request/response schema validation |
| **Email** | SMTP (configurable) | Password recovery notifications |

---

## 📂 Project Structure

```
Backend/
├── app/
│   ├── main.py                      # FastAPI application entrypoint
│   ├── api/
│   │   ├── deps.py                  # Dependency injection (DB, auth)
│   │   └── v1/                      # API v1 routes
│   │       ├── router.py            # Main router aggregator
│   │       ├── auth.py              # Login, Google OAuth
│   │       ├── users.py             # User CRUD, password reset
│   │       ├── admin.py             # Admin endpoints
│   │       ├── onboarding.py        # Questionnaire, status
│   │       ├── courses.py           # Course/subject management
│   │       ├── tasks.py             # Task CRUD
│   │       ├── schedule.py          # Fixed slots, calendar slots
│   │       ├── sync.py              # Google Calendar sync triggers
│   │       └── webhooks.py          # Google Calendar webhooks
│   ├── core/
│   │   ├── config.py                # Environment config (Pydantic)
│   │   ├── security.py              # Password hashing, JWT generation
│   │   └── utils.py                 # Password reset token utilities
│   ├── db/
│   │   ├── base.py                  # SQLAlchemy declarative base
│   │   └── session.py               # Async engine + session factory
│   ├── models/                      # SQLAlchemy ORM models
│   │   ├── user.py                  # User, UserProfile
│   │   ├── task.py                  # Course, Task
│   │   ├── schedule.py              # FixedSlot, ScheduleSlot
│   │   └── sync.py                  # CalendarSyncState
│   ├── schemas/                     # Pydantic request/response schemas
│   │   ├── user.py
│   │   ├── onboarding.py
│   │   ├── courses.py
│   │   ├── tasks.py
│   │   └── schedule.py
│   ├── services/                    # Business logic services
│   │   ├── google_oauth.py          # OAuth2 flow management
│   │   ├── calendar_service.py      # Google Calendar API wrapper
│   │   ├── sync_engine.py           # Two-way sync logic
│   │   └── email_service.py         # SMTP email service
│   └── background/
│       └── scheduler.py             # APScheduler for background tasks
├── alembic/                         # Database migrations
│   ├── versions/                    # Migration scripts
│   └── env.py                       # Alembic configuration
├── scripts/                         # Utility scripts
├── tests/                           # Test suite
├── .env.example                     # Environment template
├── requirements.txt                 # Python dependencies
├── alembic.ini                      # Alembic config
└── README.md                        # This file
```

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.11+**
- **PostgreSQL 13+**
- **Google Cloud Project** (for OAuth and Calendar API)

### 1. Clone the repository
```bash
git clone <repository-url>
cd Backend
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
Create a `.env` file in the root directory:

```env
# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/iap_db

# JWT Security
SECRET_KEY=your-secret-key-here-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=10080

# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
OAUTH_REDIRECT_URI=http://localhost:8000/api/v1/google/callback

# Webhooks (use ngrok for local development)
WEBHOOK_BASE_URL=https://your-ngrok-url.ngrok.io

# Email (for password recovery)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAILS_FROM_EMAIL=noreply@iap.com
```

### 5. Set up Google OAuth
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable **Google Calendar API**
4. Create OAuth 2.0 credentials (Web application)
5. Add authorized redirect URI: `http://localhost:8000/api/v1/google/callback`
6. Copy Client ID and Secret to `.env`

### 6. Create database
```bash
# Connect to PostgreSQL
psql -U postgres

# Create database
CREATE DATABASE iap_db;
\q
```

### 7. Run migrations
```bash
# Windows PowerShell
$env:PYTHONPATH = "."
alembic upgrade head

# macOS/Linux
PYTHONPATH=. alembic upgrade head
```

### 8. Start the server
```bash
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API**: http://localhost:8000
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

---

## 📡 API Endpoints

### Authentication (`/api/v1`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/login/access-token` | Login with username/password | ❌ |
| GET | `/google/authorize` | Get Google OAuth URL | ✅ |
| GET | `/google/callback` | OAuth callback handler | ❌ |

### User Management (`/api/v1/users`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/users/` | Register new user | ❌ |
| GET | `/users/me` | Get current user profile | ✅ |
| PUT | `/users/me/profile` | Update profile (name, major, etc.) | ✅ |
| POST | `/users/me/password` | Change password | ✅ |
| POST | `/users/password-recovery/{email}` | Request password reset | ❌ |
| POST | `/users/reset-password/` | Reset password with token | ❌ |

### Onboarding (`/api/v1/onboarding`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/onboarding/status` | Check onboarding completion | ✅ |
| POST | `/onboarding/questionnaire` | Submit initial profile data | ✅ |

### Courses (`/api/v1/courses`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/courses/` | List all user courses | ✅ |
| POST | `/courses/` | Create new course | ✅ |
| PATCH | `/courses/{id}` | Update course details | ✅ |
| DELETE | `/courses/{id}` | Delete course | ✅ |

### Tasks (`/api/v1/tasks`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/tasks/` | List tasks with filters | ✅ |
| POST | `/tasks/` | Create new task | ✅ |
| PATCH | `/tasks/{id}` | Update task | ✅ |
| DELETE | `/tasks/{id}` | Delete task | ✅ |

### Schedule (`/api/v1/schedule`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/schedule/fixed` | Get fixed busy slots | ✅ |
| POST | `/schedule/fixed` | Create fixed slot (recurring) | ✅ |
| POST | `/schedule/slots` | Create schedule slot (task instance) | ✅ |
| PUT | `/schedule/slots/{id}` | Update schedule slot | ✅ |
| DELETE | `/schedule/slots/{id}` | Delete schedule slot | ✅ |

### Calendar Sync (`/api/v1/sync`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/sync/trigger` | Manually trigger sync | ✅ |
| GET | `/sync/status` | Get sync status | ✅ |
| POST | `/sync/reset` | Reset sync state | ✅ |
| POST | `/sync/push-all` | Push all slots to Google | ✅ |
| POST | `/sync/initialize` | Initialize sync after OAuth | ✅ |

### Webhooks (`/api/v1/webhooks`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/webhooks/google-calendar` | Receive Google calendar updates | ❌ |
| POST | `/webhooks/setup` | Setup webhook channel | ✅ |

### Admin (`/api/v1/admin`)
| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/admin/users` | List all users (admin only) | ✅ |

> **Note**: For detailed request/response schemas, visit `/docs` when the server is running.

---

## 🔗 Google Calendar Integration Flow

### Initial Setup
1. **User Registration**: Create account via `POST /users/`
2. **Login**: Get JWT token via `POST /login/access-token`
3. **Authorize Google**: Call `GET /google/authorize` (returns OAuth URL)
4. **User Consent**: User grants calendar access in browser
5. **Callback**: Google redirects to `/google/callback`
6. **Token Storage**: Backend stores `refresh_token` in database
7. **Sync Initialization**: Automatically imports existing calendar events

### Two-Way Sync

#### App → Google (Write)
When user creates/updates/deletes a schedule slot:
1. Slot saved to local database
2. `CalendarService.create_event()` called
3. Event created in Google Calendar
4. `google_event_id` stored in database

#### Google → App (Read)
Two methods for importing changes:

**Method 1: Webhooks (Real-time)**
1. Backend sets up webhook channel via `POST /webhooks/setup`
2. Google sends notifications to `POST /webhooks/google-calendar`
3. `SyncEngine.sync_from_google()` fetches and applies changes

**Method 2: Manual Sync**
- User triggers `POST /sync/trigger`
- Backend fetches changes since last sync token
- Local database updated to match Google Calendar

### Important Notes
- **Webhook Expiration**: Channels expire after 7 days, auto-renewed by `APScheduler`
- **Conflict Resolution**: Local database is source of truth; manual sync overwrites local changes
- **Sync Token**: Incremental sync using `sync_token` to avoid fetching entire history

---

## 📧 Email Configuration

For password recovery functionality, configure SMTP settings:

**Gmail Example:**
1. Enable 2-Factor Authentication on your Google account
2. Generate an App Password (Security → App Passwords)
3. Add to `.env`:
```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-16-char-app-password
EMAILS_FROM_EMAIL=noreply@iap.com
```

---

## 🔒 Security Features

- **Password Hashing**: bcrypt with automatic salt generation
- **JWT Tokens**: Configurable expiration (default: 7 days)
- **CORS**: Configurable allowed origins
- **SQL Injection**: Protected via SQLAlchemy ORM
- **Input Validation**: Pydantic schemas validate all requests
- **OAuth2**: Secure Google Calendar integration with refresh tokens

---

## 📚 Additional Resources

- **API Documentation**: Available at `/docs` (Swagger UI)
- **Alternative Docs**: Available at `/redoc` (ReDoc)
- **Project Documentation**: See `About/` folder for detailed specs
- **Integration Guide**: See [INTEGRATION_GUIDE.txt](INTEGRATION_GUIDE.txt)
- **Detailed API Docs**: See [API_DOCUMENTATION.md](API_DOCUMENTATION.md)

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🎓 Project Context

This backend is part of the **L1 Intelligent Academic Planner** system, designed to demonstrate AI-powered academic scheduling with focus on:
- Human-centered design (energy management, not just time management)
- Transparent AI (explainable recommendations)
- Privacy-first architecture (user data ownership)
- Behavioral health integration (burnout prevention)

**Current Sprint**: Epic 1-2 and Story 3.1 (Foundation + Onboarding + Manual Entry)  
**Next Sprint**: AI time estimation, energy matching, dynamic rescheduling

---

<p align="center">Made with ❤️ for students struggling with time management</p>
