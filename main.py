from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from api import auth, slots, webhooks
from api.sync import router as sync_router
from persistence.database import engine
from persistence.models import Base
from background.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ──────────────────────────────────────────────────
    print("🚀 Starting Calendar Sync Backend...")
    print(f"📁 Database: {os.getenv('DATABASE_URL')}")
    print(f"🔗 Webhook URL: {os.getenv('WEBHOOK_BASE_URL')}")

    # Auto-create tables if they don't exist (safe alongside Alembic)
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables verified / created")

    # Start background jobs (webhook renewal + periodic sync)
    start_scheduler()

    yield

    # ── Shutdown ─────────────────────────────────────────────────
    stop_scheduler()
    print("👋 Shutting down...")

app = FastAPI(
    title="Calendar Sync Backend",
    description="Two-way Google Calendar synchronization",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, tags=["Authentication"])
app.include_router(slots.router, tags=["Slots"])
app.include_router(webhooks.router, tags=["Webhooks"])
app.include_router(sync_router, tags=["Sync"])

@app.get("/")
def root():
    return {
        "message": "Calendar Sync Backend API",
        "docs": "/docs",
        "health": "/health",
        "endpoints": {
            "auth": "/auth  (OAuth + user management)",
            "slots": "/slots  (CRUD → Google Calendar)",
            "sync": "/sync  (manual sync + status)",
            "webhooks": "/webhooks  (Google push notifications)",
        },
    }

@app.get("/health")
def health_check():
    google_configured = all([
        os.getenv("GOOGLE_CLIENT_ID"),
        os.getenv("GOOGLE_CLIENT_SECRET"),
        os.getenv("OAUTH_REDIRECT_URI"),
    ])
    return {
        "status": "healthy",
        "google_calendar_configured": google_configured,
        "webhook_url_set": bool(os.getenv("WEBHOOK_BASE_URL")),
        "database_url_set": bool(os.getenv("DATABASE_URL")),
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("DEBUG", "False").lower() == "true"
    )
