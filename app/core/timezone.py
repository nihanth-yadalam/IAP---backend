"""
Timezone helpers — canonical UTC normalization for the project.

Policy:
  • Store absolute datetimes in UTC in the DB (timezone-aware columns).
  • Store user timezone as IANA name on UserProfile.timezone.
  • Convert to/from user-local time only at API edges and display.
  • Recurring/local-time slots (day_of_week + start_time/end_time) are
    interpreted in the user's IANA zone when building concrete datetimes.
"""

from datetime import datetime
from zoneinfo import ZoneInfo


_UTC = ZoneInfo("UTC")


def validate_timezone(tzname: str) -> bool:
    """Return True if *tzname* is a valid IANA timezone identifier."""
    try:
        ZoneInfo(tzname)
        return True
    except (KeyError, Exception):
        return False


def safe_zone(tzname: str | None) -> ZoneInfo:
    """Return a ZoneInfo for *tzname*, falling back to UTC on any error."""
    if not tzname:
        return _UTC
    try:
        return ZoneInfo(tzname)
    except (KeyError, Exception):
        return _UTC


def to_utc(dt: datetime, tzname: str | None = None) -> datetime:
    """
    Normalize *dt* to a timezone-aware UTC datetime.

    • If *dt* is already tz-aware → convert to UTC.
    • If *dt* is naive and *tzname* is given → interpret as local in that
      zone, then convert to UTC.
    • If *dt* is naive and *tzname* is None → assume UTC and attach tzinfo.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(_UTC)
    tz = safe_zone(tzname)
    return dt.replace(tzinfo=tz).astimezone(_UTC)


def from_utc(dt: datetime, tzname: str) -> datetime:
    """
    Convert a UTC (or tz-aware) datetime to the user's local timezone.

    If *dt* is naive it is assumed to be UTC.
    """
    tz = safe_zone(tzname)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_UTC)
    return dt.astimezone(tz)


def utc_iso(dt: datetime, tzname: str | None = None) -> str:
    """
    Return an ISO-8601 string in UTC suitable for Google Calendar API.

    The string always ends with ``+00:00`` (Python default for UTC-aware
    datetimes). Google Calendar interprets this correctly when paired
    with ``"timeZone": "UTC"`` in the event body.
    """
    return to_utc(dt, tzname).isoformat()
