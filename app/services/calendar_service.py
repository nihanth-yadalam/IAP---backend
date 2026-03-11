"""
Google Calendar API wrapper — from System B.
Creates / updates / deletes events, sets up webhook channels.
Adapted: accepts refresh_token directly instead of user_id lookups.
"""

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback
from datetime import datetime, timedelta
import uuid

from app.core.timezone import to_utc, utc_iso
from app.services.google_oauth import GoogleOAuthService


class CalendarService:
    def __init__(self, oauth_service: GoogleOAuthService):
        self.oauth_service = oauth_service

    # ── Event CRUD ───────────────────────────────────────────────────

    def create_event(self, refresh_token: str, calendar_id: str, slot_data: dict) -> str:
        creds = self.oauth_service.get_valid_credentials(refresh_token)
        service = build("calendar", "v3", credentials=creds)

        event_body = self._build_event_body(slot_data)
        event = service.events().insert(calendarId=calendar_id, body=event_body).execute()
        return event["id"]

    def update_event(self, refresh_token: str, calendar_id: str, google_event_id: str, slot_data: dict):
        creds = self.oauth_service.get_valid_credentials(refresh_token)
        service = build("calendar", "v3", credentials=creds)

        event_body = self._build_event_body(slot_data)
        service.events().update(
            calendarId=calendar_id, eventId=google_event_id, body=event_body
        ).execute()

    @staticmethod
    def _build_event_body(slot_data: dict) -> dict:
        """Build a Google Calendar event body with UTC-normalized datetimes."""
        start_utc = to_utc(slot_data["google_start_datetime"])
        end_utc = to_utc(slot_data["google_end_datetime"])
        print(f"[calendar] Sending to Google: start={start_utc.isoformat()} end={end_utc.isoformat()} (UTC)")
        return {
            "summary": slot_data["title"],
            "start": {"dateTime": start_utc.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_utc.isoformat(), "timeZone": "UTC"},
        }

    def delete_event(self, refresh_token: str, calendar_id: str, google_event_id: str):
        if not google_event_id:
            return

        creds = self.oauth_service.get_valid_credentials(refresh_token)
        service = build("calendar", "v3", credentials=creds)

        try:
            service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
        except HttpError as e:
            status = getattr(getattr(e, "resp", None), "status", None)
            if status == 410:
                print(f"Google event {google_event_id} already deleted (410)")
                return
            print(f"HttpError deleting event {google_event_id}: {e}")
            traceback.print_exc()
            raise

    # ── Webhook ──────────────────────────────────────────────────────

    def setup_webhook_channel(self, refresh_token: str, calendar_id: str, user_id: int, webhook_url: str) -> dict:
        creds = self.oauth_service.get_valid_credentials(refresh_token)
        service = build("calendar", "v3", credentials=creds)

        channel_body = {
            "id": f"channel-{user_id}-{uuid.uuid4()}",
            "type": "web_hook",
            "address": webhook_url,
            "expiration": int((datetime.utcnow() + timedelta(days=7)).timestamp() * 1000),
        }
        response = service.events().watch(calendarId=calendar_id, body=channel_body).execute()
        return response

    # ── Event listing (for sync) ─────────────────────────────────────

    def list_events(self, refresh_token: str, calendar_id: str, sync_token: str | None = None) -> dict:
        creds = self.oauth_service.get_valid_credentials(refresh_token)
        service = build("calendar", "v3", credentials=creds)

        all_items = []
        page_token = None

        while True:
            if sync_token and not page_token:
                # Incremental sync — use syncToken for first request only
                result = service.events().list(
                    calendarId=calendar_id,
                    syncToken=sync_token,
                    pageToken=page_token,
                ).execute()
            elif page_token:
                # Follow-up pages (works for both incremental and full sync)
                result = service.events().list(
                    calendarId=calendar_id,
                    pageToken=page_token,
                ).execute()
            else:
                # Full sync — fetch recent events
                time_min = (datetime.utcnow() - timedelta(days=30)).isoformat() + "Z"
                result = service.events().list(
                    calendarId=calendar_id,
                    singleEvents=True,
                    timeMin=time_min,
                    orderBy="startTime",
                ).execute()

            all_items.extend(result.get("items", []))

            page_token = result.get("nextPageToken")
            if not page_token:
                break

        # Return combined result with the final sync token
        return {
            "items": all_items,
            "nextSyncToken": result.get("nextSyncToken"),
        }
