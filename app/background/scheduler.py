"""
Background scheduler — from System B, adapted for async.
Periodically:
  1. Renew expiring Google Calendar webhook channels.
  2. Run incremental sync for all users with valid tokens.
  3. Run reflexion sweep for users needing reflexion updates.
"""

import asyncio
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select, or_

from app.db.session import async_session
from app.models.user import User, UserProfile
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


# ── Scheduled reflexion sweep ────────────────────────────────────────

async def scheduled_reflexion_sweep():
    """
    Run reflexion agent for users who need it.
    Queries users where last_reflexion_at IS NULL or last_reflexion_at < NOW() - 3 days.
    Processes users sequentially to avoid DB overload.
    """
    from app.services.reflexion_agent import run_reflexion_agent

    async with async_session() as db:
        threshold = datetime.now(timezone.utc) - timedelta(days=3)

        result = await db.execute(
            select(UserProfile.user_id).where(
                or_(
                    UserProfile.last_reflexion_at == None,
                    UserProfile.last_reflexion_at < threshold,
                )
            )
        )
        user_ids = [row[0] for row in result.all()]

        if not user_ids:
            print("[Scheduler] Reflexion sweep: no users need reflexion.")
            return

        print(f"[Scheduler] Reflexion sweep starting for {len(user_ids)} users.")
        for uid in user_ids:
            try:
                await run_reflexion_agent(uid, db, trigger="scheduled")
                print(f"[Scheduler] Reflexion complete for user {uid}")
            except Exception as e:
                print(f"[Scheduler] Reflexion failed for user {uid}: {e}")
        print("[Scheduler] Reflexion sweep complete.")


# ── Scheduler setup ──────────────────────────────────────────────────

scheduler = AsyncIOScheduler()


def start_scheduler():
    """Start the background job scheduler."""
    # Renew webhooks every 12 hours
    scheduler.add_job(renew_webhooks, "interval", hours=12, id="renew_webhooks")
    # Periodic sync every 15 minutes
    scheduler.add_job(periodic_sync, "interval", minutes=15, id="periodic_sync")
    # Reflexion sweep every 3 days
    scheduler.add_job(scheduled_reflexion_sweep, "interval", days=3, id="reflexion_sweep")
    scheduler.start()
    print("[Scheduler] Background scheduler started.")


def stop_scheduler():
    """Gracefully shut down the scheduler."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
        print("[Scheduler] Background scheduler stopped.")
