"""
Background scheduler — from System B, adapted for async.
Periodically:
  1. Renew expiring Google Calendar webhook channels.
  2. Run incremental sync for all users with valid tokens.
"""

import asyncio
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select

from app.db.session import async_session
from app.models.user import User
from app.models.sync import CalendarSyncState
from app.core.config import settings
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService
from app.services.sync_engine import SyncEngine


def _build_sync_engine() -> SyncEngine:
    oauth = GoogleOAuthService()
    cal = CalendarService(oauth)
    return SyncEngine(oauth, cal)


# ── Webhook renewal ──────────────────────────────────────────────────

async def renew_webhooks():
    """Renew webhook channels expiring within the next 24 hours."""
    async with async_session() as db:
        threshold = datetime.utcnow() + timedelta(hours=24)

        result = await db.execute(
            select(CalendarSyncState).where(
                CalendarSyncState.webhook_expires_at != None,
                CalendarSyncState.webhook_expires_at < threshold,
            )
        )
        states = result.scalars().all()

        if not states:
            return

        cal = CalendarService(GoogleOAuthService())

        for state in states:
            user = await db.get(User, state.user_id)
            if not user or not user.google_refresh_token:
                continue

            webhook_url = None
            if settings.WEBHOOK_BASE_URL:
                webhook_url = f"{settings.WEBHOOK_BASE_URL}/api/v1/webhooks/google-calendar"
            if not webhook_url:
                continue

            try:
                calendar_id = state.google_calendar_id or "primary"
                response = cal.setup_webhook_channel(
                    user.google_refresh_token, calendar_id, user.id, webhook_url
                )
                state.webhook_channel_id = response.get("id")
                state.webhook_resource_id = response.get("resourceId")
                exp_raw = response.get("expiration")
                if exp_raw:
                    try:
                        state.webhook_expires_at = datetime.fromtimestamp(int(exp_raw) / 1000)
                    except (ValueError, TypeError):
                        pass
                await db.commit()
                print(f"[Scheduler] Renewed webhook for user {state.user_id}")
            except Exception as e:
                print(f"[Scheduler] Failed to renew webhook for user {state.user_id}: {e}")


# ── Periodic sync ────────────────────────────────────────────────────

async def periodic_sync():
    """Run incremental Google Calendar sync for all users with valid tokens."""
    async with async_session() as db:
        result = await db.execute(
            select(User).where(User.google_refresh_token != None)
        )
        users = result.scalars().all()

        if not users:
            return

        engine = _build_sync_engine()
        for user in users:
            try:
                await engine.sync_from_google(db, user.id)
                print(f"[Scheduler] Synced user {user.id}")
            except Exception as e:
                print(f"[Scheduler] Sync failed for user {user.id}: {e}")


# ── Scheduler setup ──────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Start the background job scheduler."""
    # Renew webhooks every 12 hours
    scheduler.add_job(renew_webhooks, "interval", hours=12, id="renew_webhooks")
    # Periodic sync every 15 minutes
    scheduler.add_job(periodic_sync, "interval", minutes=15, id="periodic_sync")
    scheduler.start()
    print("[Scheduler] Background scheduler started.")


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Background scheduler stopped.")
