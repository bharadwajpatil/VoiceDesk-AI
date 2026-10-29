"""Tests for Google Calendar service with mocked Google API."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from services.calendar_service import GoogleCalendarService


@pytest.fixture
def calendar_service() -> GoogleCalendarService:
    """Create a GoogleCalendarService pointing to temporary credentials."""
    with tempfile.TemporaryDirectory() as tmpdir:
        token_path = Path(tmpdir) / "test_token.json"
        service = GoogleCalendarService(
            client_id="mock_client_id.apps.googleusercontent.com",
            client_secret="mock_client_secret",
            redirect_uri="http://localhost:8000/callback",
            calendar_id="primary",
            token_file=token_path,
        )
        yield service


def test_calendar_service_configuration(
    calendar_service: GoogleCalendarService,
) -> None:
    """Test configuration status checks."""
    assert calendar_service.is_configured() is True
    # Without a saved token file, it must report not connected
    assert calendar_service.is_connected() is False

    unconfigured = GoogleCalendarService(client_id="", client_secret="")
    assert unconfigured.is_configured() is False


def test_check_calendar_slot_mocked_available(
    calendar_service: GoogleCalendarService,
) -> None:
    """Test conflict check when the calendar has no overlapping events."""
    mock_api = MagicMock()
    # Mock empty events list
    mock_api.events().list().execute.return_value = {"items": []}

    with patch.object(calendar_service, "get_calendar_client", return_value=mock_api):
        is_free, msg = calendar_service.check_calendar_slot("2026-10-15", "14:00")
        assert is_free is True
        assert "available" in msg.lower()


def test_check_calendar_slot_mocked_conflict(
    calendar_service: GoogleCalendarService,
) -> None:
    """Test conflict check when an existing event conflicts with the requested slot."""
    mock_api = MagicMock()
    mock_api.events().list().execute.return_value = {
        "items": [
            {
                "id": "existing_event_1",
                "summary": "Existing Meeting",
                "status": "confirmed",
            }
        ]
    }

    with patch.object(calendar_service, "get_calendar_client", return_value=mock_api):
        is_free, msg = calendar_service.check_calendar_slot("2026-10-15", "14:00")
        assert is_free is False
        assert "existing calendar event" in msg


def test_create_event_mocked_success(calendar_service: GoogleCalendarService) -> None:
    """Test successful event creation returns the created event ID."""
    mock_api = MagicMock()
    mock_api.events().insert().execute.return_value = {"id": "google_event_999"}

    with patch.object(calendar_service, "get_calendar_client", return_value=mock_api):
        success, event_id = calendar_service.create_event(
            customer_name="Hannah Montana",
            customer_phone="+15559876543",
            appointment_date="2026-10-20",
            appointment_time="11:00",
            service_type="VIP Session",
        )
        assert success is True
        assert event_id == "google_event_999"


def test_create_event_mocked_failure(calendar_service: GoogleCalendarService) -> None:
    """Test handling of Google API exceptions during event creation."""
    mock_api = MagicMock()
    mock_api.events().insert().execute.side_effect = Exception(
        "Google 503 Backend Error"
    )

    with patch.object(calendar_service, "get_calendar_client", return_value=mock_api):
        success, err_msg = calendar_service.create_event(
            customer_name="Ian Malcolm",
            customer_phone="+15559876543",
            appointment_date="2026-10-20",
            appointment_time="11:00",
            service_type="Tour",
        )
        assert success is False
        assert "Google 503 Backend Error" in err_msg


def test_delete_event_mocked(calendar_service: GoogleCalendarService) -> None:
    """Test deleting a calendar event."""
    mock_api = MagicMock()
    mock_api.events().delete().execute.return_value = {}

    with patch.object(calendar_service, "get_calendar_client", return_value=mock_api):
        result = calendar_service.delete_event("google_event_999")
        assert result is True
