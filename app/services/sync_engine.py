"""
Two-way sync engine — from System B, adapted for async DB.

All Google API calls are synchronous (google-api-python-client is sync),
so sync methods are called inside `asyncio.to_thread` from the endpoint layer.
The engine itself stays synchronous to keep Google SDK usage straightforward.
"""

from googleapiclient.errors import HttpError
from datetime import datetime, timedelta
from dateutil import parser as date_parser
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schedule import FixedSlot
from app.models.sync import CalendarSyncState
from app.models.user import User
from app.services.google_oauth import GoogleOAuthService
from app.services.calendar_service import CalendarService


class SyncEngine:
    def __init__(self, oauth_service: GoogleOAuthService, calendar_service: CalendarService):
        self.oauth_service = oauth_service
        self.calendar_service = calendar_service

    # ──────────────────────────────────────────────────────────────────
    # Push local → Google
    # ──────────────────────────────────────────────────────────────────

    async def push_to_google(self, db: AsyncSession, user_id: int, slot_id: int):
        """Push a single slot from app DB to Google Calendar."""
        user = await db.get(User, user_id)
        if not user or not user.google_refresh_token:
            return

        result = await db.execute(select(FixedSlot).where(FixedSlot.id == slot_id))
        slot = result.scalars().first()
        if not slot or slot.last_updated_source != "APP":
            return

        sync_state = await self._get_sync_state(db, user_id)
        calendar_id = sync_state.google_calendar_id if sync_state else "primary"
        refresh_token = user.google_refresh_token

        try:
            if not slot.is_google_event:
                # Create new event
                google_event_id = self.calendar_service.create_event(
                    refresh_token, calendar_id,
                    {
                        "title": slot.title,
                        "google_start_datetime": slot.google_start_datetime,
                        "google_end_datetime": slot.google_end_datetime,
                    },
                )
                slot.google_event_id = google_event_id
                slot.is_google_event = True
                slot.last_updated_source = "APP"
                slot.last_updated_at = datetime.utcnow()
                await db.commit()
            else:
                if slot.is_deleted:
                    try:
                        self.calendar_service.delete_event(refresh_token, calendar_id, slot.google_event_id)
                    except HttpError as e:
                        if getattr(getattr(e, "resp", None), "status", None) == 410:
                            slot.is_google_event = False
                            slot.google_event_id = None
                            await db.commit()
                        else:
                            raise
                else:
                    try:
                        self.calendar_service.update_event(
                            refresh_token, calendar_id, slot.google_event_id,
                            {
                                "title": slot.title,
                                "google_start_datetime": slot.google_start_datetime,
                                "google_end_datetime": slot.google_end_datetime,
                            },
                        )
                    except HttpError as e:
                        if getattr(getattr(e, "resp", None), "status", None) == 410:
                            new_id = self.calendar_service.create_event(
                                refresh_token, calendar_id,
                                {
                                    "title": slot.title,
                                    "google_start_datetime": slot.google_start_datetime,
                                    "google_end_datetime": slot.google_end_datetime,
                                },
                            )
                            slot.google_event_id = new_id
                            slot.is_google_event = True
                            slot.last_updated_source = "APP"
                            slot.last_updated_at = datetime.utcnow()
                            await db.commit()
                        else:
                            raise
        except Exception as e:
            print(f"Error pushing to Google: {e}")
            raise

    # ──────────────────────────────────────────────────────────────────
    # Pull Google → local
    # ──────────────────────────────────────────────────────────────────

    async def sync_from_google(self, db: AsyncSession, user_id: int):
        """Fetch changes from Google Calendar (incremental sync)."""
        user = await db.get(User, user_id)
        if not user or not user.google_refresh_token:
            print(f"[sync] User {user_id} has no refresh token, skipping")
            return

        sync_state = await self._get_sync_state(db, user_id)
        calendar_id = sync_state.google_calendar_id if sync_state else "primary"
        sync_token = sync_state.sync_token if sync_state else None

        print(f"[sync] Starting pull for user {user_id}, calendar={calendar_id}, has_sync_token={sync_token is not None}")

        try:
            events_result = self.calendar_service.list_events(
                user.google_refresh_token, calendar_id, sync_token
            )

            items = events_result.get("items", [])
            print(f"[sync] Fetched {len(items)} events from Google Calendar")

            imported = 0
            skipped = 0
            for event in items:
                try:
                    was_imported = await self._process_google_event(db, user_id, event)
                    if was_imported:
                        imported += 1
                    else:
                        skipped += 1
                except Exception as e:
                    print(f"[sync] Error processing event {event.get('id', '?')}: {e}")

            print(f"[sync] Done: imported={imported}, skipped={skipped}")

            new_sync_token = events_result.get("nextSyncToken")
            if new_sync_token:
                await self._update_sync_token(db, user_id, new_sync_token)
                print(f"[sync] Sync token updated")

        except HttpError as e:
            status_code = getattr(getattr(e, "resp", None), "status", None)
            print(f"[sync] HttpError {status_code}: {e}")
            if status_code == 410:
                print("[sync] Sync token expired, performing full resync")
                await self._full_resync(db, user_id)
            else:
                raise
        except Exception as e:
            print(f"[sync] Unexpected error: {e}")
            raise

    async def _process_google_event(self, db: AsyncSession, user_id: int, event: dict) -> bool:
        """Process a single Google Calendar event. Returns True if imported/updated."""
        google_event_id = event.get("id")
        if not google_event_id:
            return False

        # Check if this event was pushed from a Task (keep task in sync)
        from app.models.task import Task
        task_result = await db.execute(
            select(Task).where(Task.google_event_id == google_event_id, Task.user_id == user_id)
        )
        existing_task = task_result.scalars().first()

        # Check if this event already exists as a FixedSlot
        slot_result = await db.execute(
            select(FixedSlot).where(FixedSlot.google_event_id == google_event_id)
        )
        existing_slot = slot_result.scalars().first()

        # Handle deleted/cancelled events
        if event.get("status") == "cancelled":
            if existing_task:
                print(f"[sync] Event '{existing_task.title}' deleted in Google → deleting task from Schedora")
                await db.delete(existing_task)
                await db.commit()
            if existing_slot:
                existing_slot.is_deleted = True
                existing_slot.last_updated_source = "GOOGLE"
                existing_slot.last_updated_at = datetime.utcnow()
                await db.commit()
            return True

        # Parse start/end — skip events that don't have proper time info
        start_raw = event.get("start")
        end_raw = event.get("end")
        if not start_raw or not end_raw:
            print(f"[sync] Skipping event {google_event_id}: missing start/end")
            return False

        parsed_start = self._parse_datetime(start_raw)
        parsed_end = self._parse_datetime(end_raw)
        title = event.get("summary", "Untitled")

        # ── Update existing Task (pushed from Schedora) ──
        if existing_task:
            existing_task.title = title
            existing_task.scheduled_start_time = parsed_start
            existing_task.scheduled_end_time = parsed_end
            await db.commit()
            return True

        # ── Update existing FixedSlot ──
        if existing_slot:
            event_data = {
                "title": title,
                "google_start_datetime": parsed_start,
                "google_end_datetime": parsed_end,
                "google_event_id": google_event_id,
                "is_google_event": True,
                "last_updated_source": "GOOGLE",
                "last_updated_at": datetime.utcnow(),
            }
            if existing_slot.last_updated_source == "APP" and self._events_match(existing_slot, event_data):
                return False  # No change
            for key, value in event_data.items():
                setattr(existing_slot, key, value)
            await db.commit()
            return True

        # ── New event from Google → create as FixedSlot (busy slot) ──
        new_slot = FixedSlot(
            user_id=user_id,
            title=title,
            google_start_datetime=parsed_start,
            google_end_datetime=parsed_end,
            google_event_id=google_event_id,
            is_google_event=True,
            last_updated_source="GOOGLE",
            last_updated_at=datetime.utcnow(),
        )
        db.add(new_slot)
        await db.commit()
        print(f"[sync] Imported event '{title}' as busy slot")
        return True

    def _events_match(self, slot, event_data: dict) -> bool:
        time_tolerance = timedelta(seconds=5)
        start_match = abs(
            slot.google_start_datetime.replace(tzinfo=None)
            - event_data["google_start_datetime"].replace(tzinfo=None)
        ) < time_tolerance
        end_match = abs(
            slot.google_end_datetime.replace(tzinfo=None)
            - event_data["google_end_datetime"].replace(tzinfo=None)
        ) < time_tolerance
        title_match = slot.title == event_data["title"]
        return start_match and end_match and title_match

    def _parse_datetime(self, dt_dict: dict) -> datetime:
        if "dateTime" in dt_dict:
            return date_parser.parse(dt_dict["dateTime"])
        elif "date" in dt_dict:
            return datetime.fromisoformat(dt_dict["date"])
        return datetime.utcnow()

    async def _full_resync(self, db: AsyncSession, user_id: int):
        await self._update_sync_token(db, user_id, None)
        await self.sync_from_google(db, user_id)

    # ── Helpers ──────────────────────────────────────────────────────

    async def _get_sync_state(self, db: AsyncSession, user_id: int) -> CalendarSyncState | None:
        result = await db.execute(
            select(CalendarSyncState).where(CalendarSyncState.user_id == user_id)
        )
        return result.scalars().first()

    async def _update_sync_token(self, db: AsyncSession, user_id: int, sync_token: str | None):
        state = await self._get_sync_state(db, user_id)
        if not state:
            state = CalendarSyncState(user_id=user_id)
            db.add(state)
        state.sync_token = sync_token
        state.last_synced_at = datetime.utcnow()
        await db.commit()

    async def initialize_sync(self, db: AsyncSession, user_id: int, webhook_url: str | None = None) -> dict:
        """
        Initialize calendar sync for a user:
        1. Create CalendarSyncState if missing
        2. Perform initial pull from Google
        3. Setup webhook channel
        """
        result_info = {"sync_state": "created", "initial_sync": "skipped", "webhook": "skipped"}

        user = await db.get(User, user_id)
        if not user or not user.google_refresh_token:
            result_info["initial_sync"] = "failed: no refresh token"
            return result_info

        # 1. Ensure sync state exists
        state = await self._get_sync_state(db, user_id)
        if not state:
            state = CalendarSyncState(user_id=user_id, google_calendar_id="primary")
            db.add(state)
            await db.commit()
            result_info["sync_state"] = "created"
        else:
            result_info["sync_state"] = "already_exists"

        # 2. Initial sync
        try:
            await self.sync_from_google(db, user_id)
            result_info["initial_sync"] = "completed"
        except Exception as exc:
            result_info["initial_sync"] = f"failed: {exc}"

        # 3. Webhook
        if webhook_url:
            try:
                calendar_id = state.google_calendar_id or "primary"
                response = self.calendar_service.setup_webhook_channel(
                    user.google_refresh_token, calendar_id, user_id, webhook_url
                )
                expiration_raw = response.get("expiration")
                webhook_expires_at = None
                if expiration_raw is not None:
                    try:
                        webhook_expires_at = datetime.fromtimestamp(int(expiration_raw) / 1000)
                    except (ValueError, TypeError):
                        pass

                state.webhook_channel_id = response.get("id")
                state.webhook_resource_id = response.get("resourceId")
                state.webhook_expires_at = webhook_expires_at
                await db.commit()
                result_info["webhook"] = "configured"
            except Exception as exc:
                result_info["webhook"] = f"failed: {exc}"
        else:
            result_info["webhook"] = "skipped (no webhook URL)"

        return result_info
