import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta
from app.services.calendar_service import CalendarService
from app.services.google_oauth import GoogleOAuthService

@pytest.fixture
def mock_oauth_service():
    service = MagicMock(spec=GoogleOAuthService)
    service.get_valid_credentials.return_value = MagicMock()
    return service

@pytest.fixture
def calendar_service(mock_oauth_service):
    return CalendarService(mock_oauth_service)

def test_create_event(calendar_service):
    with patch("app.services.calendar_service.build") as mock_build:
        # Setup mock
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_insert = MagicMock()
        mock_execute = MagicMock()
        
        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.insert.return_value = mock_insert
        # execute() should return the dict, not another mock
        mock_insert.execute.return_value = {"id": "new_event_id"}
        
        # Call
        slot_data = {
            "title": "Test Event",
            "google_start_datetime": datetime.utcnow(),
            "google_end_datetime": datetime.utcnow() + timedelta(hours=1)
        }
        event_id = calendar_service.create_event("refresh_token", "primary", slot_data)
        
        # Assert
        assert event_id == "new_event_id"
        mock_events.insert.assert_called_once()
        args, kwargs = mock_events.insert.call_args
        assert kwargs["calendarId"] == "primary"
        assert kwargs["body"]["summary"] == "Test Event"

def test_delete_event(calendar_service):
    with patch("app.services.calendar_service.build") as mock_build:
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_delete = MagicMock()
        
        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.delete.return_value = mock_delete
        
        calendar_service.delete_event("refresh_token", "primary", "event_id")
        
        mock_events.delete.assert_called_once_with(calendarId="primary", eventId="event_id")

def test_list_events(calendar_service):
    with patch("app.services.calendar_service.build") as mock_build:
        mock_service = MagicMock()
        mock_events = MagicMock()
        mock_list = MagicMock()
        
        mock_build.return_value = mock_service
        mock_service.events.return_value = mock_events
        mock_events.list.return_value = mock_list
        
        # execute() must return the dict directly (not a MagicMock wrapper)
        mock_list.execute.return_value = {
            "items": [{"id": "ev1", "summary": "Event 1"}],
            "nextPageToken": None,
            "nextSyncToken": "sync_token_123"
        }
        
        result = calendar_service.list_events("refresh_token", "primary")
        
        assert len(result["items"]) == 1
        assert result["items"][0]["id"] == "ev1"
        assert result["nextSyncToken"] == "sync_token_123"
