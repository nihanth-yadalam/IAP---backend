"""
Tests for app.core.timezone helpers and service-level UTC normalization.
"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from app.core.timezone import to_utc, from_utc, validate_timezone, safe_zone, utc_iso

# ─────────────────────────────────────────────────────────────────────
# validate_timezone
# ─────────────────────────────────────────────────────────────────────

class TestValidateTimezone:
    def test_valid_iana(self):
        assert validate_timezone("America/New_York") is True
        assert validate_timezone("Asia/Kolkata") is True
        assert validate_timezone("UTC") is True

    def test_invalid(self):
        assert validate_timezone("Mars/Olympus") is False
        assert validate_timezone("") is False

# ─────────────────────────────────────────────────────────────────────
# safe_zone
# ─────────────────────────────────────────────────────────────────────

class TestSafeZone:
    def test_valid(self):
        tz = safe_zone("America/Chicago")
        assert tz.key == "America/Chicago"

    def test_none_fallback(self):
        assert safe_zone(None).key == "UTC"

    def test_invalid_fallback(self):
        assert safe_zone("NotA/Zone").key == "UTC"

# ─────────────────────────────────────────────────────────────────────
# to_utc
# ─────────────────────────────────────────────────────────────────────

class TestToUtc:
    def test_aware_non_utc(self):
        """A datetime in US/Eastern should be shifted to UTC."""
        eastern = ZoneInfo("America/New_York")
        local_dt = datetime(2024, 6, 15, 10, 0, tzinfo=eastern)  # 10 AM EDT = UTC-4
        result = to_utc(local_dt)
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0
        assert result.hour == 14  # 10 + 4

    def test_aware_utc_passthrough(self):
        utc = ZoneInfo("UTC")
        dt = datetime(2024, 1, 1, 12, 0, tzinfo=utc)
        result = to_utc(dt)
        assert result == dt

    def test_naive_with_tzname(self):
        """Naive datetime + tzname → treat as local in that zone, convert to UTC."""
        result = to_utc(datetime(2024, 6, 15, 10, 0), "America/New_York")
        assert result.utcoffset().total_seconds() == 0
        assert result.hour == 14

    def test_naive_no_tzname(self):
        """Naive datetime without tzname → assumed UTC."""
        dt = datetime(2024, 1, 1, 5, 0)
        result = to_utc(dt)
        assert result.hour == 5
        assert result.utcoffset().total_seconds() == 0

    def test_dst_spring_forward(self):
        """US/Eastern spring forward: 2:30 AM local skips to 3 AM (EDT offset -4)."""
        # 2024-03-10 02:30 doesn't strictly exist (spring forward).
        # ZoneInfo resolves the gap; just assert it converts without error.
        result = to_utc(datetime(2024, 3, 10, 2, 30), "America/New_York")
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0

    def test_dst_fall_back(self):
        """US/Eastern fall back: 1:30 AM is ambiguous. ZoneInfo picks post-transition."""
        result = to_utc(datetime(2024, 11, 3, 1, 30), "America/New_York")
        assert result.tzinfo is not None
        assert result.utcoffset().total_seconds() == 0


# ─────────────────────────────────────────────────────────────────────
# from_utc
# ─────────────────────────────────────────────────────────────────────

class TestFromUtc:
    def test_to_eastern(self):
        utc_dt = datetime(2024, 6, 15, 14, 0, tzinfo=ZoneInfo("UTC"))
        local = from_utc(utc_dt, "America/New_York")
        assert local.hour == 10
        assert str(local.tzinfo) == "America/New_York"

    def test_naive_assumed_utc(self):
        """Naive input is assumed UTC then converted."""
        local = from_utc(datetime(2024, 6, 15, 14, 0), "America/New_York")
        assert local.hour == 10

    def test_roundtrip(self):
        """to_utc ↔ from_utc roundtrip preserves the same point in time."""
        eastern = ZoneInfo("America/New_York")
        original = datetime(2024, 6, 15, 10, 0, tzinfo=eastern)
        utc = to_utc(original)
        back = from_utc(utc, "America/New_York")
        assert back.hour == 10
        assert back.year == 2024


# ─────────────────────────────────────────────────────────────────────
# utc_iso
# ─────────────────────────────────────────────────────────────────────

class TestUtcIso:
    def test_aware(self):
        dt = datetime(2024, 6, 15, 10, 0, tzinfo=ZoneInfo("America/New_York"))
        iso = utc_iso(dt)
        assert "+00:00" in iso or iso.endswith("Z")
        assert "14:00" in iso  # 10 EDT → 14 UTC

    def test_naive_with_tz(self):
        iso = utc_iso(datetime(2024, 6, 15, 10, 0), "Asia/Kolkata")
        assert "+00:00" in iso or iso.endswith("Z")
        # IST is UTC+5:30 → 10:00 IST = 04:30 UTC
        assert "04:30" in iso


# ─────────────────────────────────────────────────────────────────────
# CalendarService._build_event_body (unit test — no Google API call)
# ─────────────────────────────────────────────────────────────────────

class TestBuildEventBody:
    def test_utc_payload(self):
        """Verify the event body sent to Google has UTC times and timeZone:'UTC'."""
        from app.services.calendar_service import CalendarService

        eastern = ZoneInfo("America/New_York")
        slot_data = {
            "title": "Study Session",
            "google_start_datetime": datetime(2024, 6, 15, 10, 0, tzinfo=eastern),
            "google_end_datetime": datetime(2024, 6, 15, 11, 0, tzinfo=eastern),
        }
        body = CalendarService._build_event_body(slot_data)

        assert body["summary"] == "Study Session"
        assert body["start"]["timeZone"] == "UTC"
        assert body["end"]["timeZone"] == "UTC"
        # 10 AM EDT → 14:00 UTC
        assert "14:00" in body["start"]["dateTime"]
        assert "15:00" in body["end"]["dateTime"]

    def test_naive_utc_assumed(self):
        """Naive datetimes are assumed UTC and passed through."""
        from app.services.calendar_service import CalendarService

        slot_data = {
            "title": "Meeting",
            "google_start_datetime": datetime(2024, 1, 1, 9, 0),
            "google_end_datetime": datetime(2024, 1, 1, 10, 0),
        }
        body = CalendarService._build_event_body(slot_data)
        assert "09:00" in body["start"]["dateTime"]
        assert "10:00" in body["end"]["dateTime"]
