"""Google Calendar OAuth and Event Synchronization Service.

Handles OAuth 2.0 authorization, token persistence, conflict detection,
and bidirectional calendar synchronization for VoiceDesk AI.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from config import (
    BUSINESS_NAME,
    BUSINESS_TIMEZONE,
    GOOGLE_CALENDAR_ID,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
    GOOGLE_TOKEN_FILE,
)
from utils.logging import setup_logger

logger = setup_logger("voicedesk.calendar")

# Minimal required scope for appointment event management
CALENDAR_SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


class GoogleCalendarService:
    """Service for interacting with Google Calendar API using OAuth 2.0."""

    def __init__(
        self,
        client_id: str | None = None,
        client_secret: str | None = None,
        redirect_uri: str | None = None,
        calendar_id: str | None = None,
        token_file: str | Path | None = None,
        timezone_name: str = BUSINESS_TIMEZONE,
    ) -> None:
        self.client_id = GOOGLE_CLIENT_ID if client_id is None else client_id
        self.client_secret = (
            GOOGLE_CLIENT_SECRET if client_secret is None else client_secret
        )
        self.redirect_uri = (
            GOOGLE_REDIRECT_URI if redirect_uri is None else redirect_uri
        )
        self.calendar_id = GOOGLE_CALENDAR_ID if calendar_id is None else calendar_id
        self.token_file = Path(GOOGLE_TOKEN_FILE if token_file is None else token_file)
        self.timezone_name = timezone_name
        self._service: Any = None

    def is_configured(self) -> bool:
        """Check if OAuth client credentials are configured."""
        return bool(self.client_id and self.client_secret)

    def is_connected(self) -> bool:
        """Check if a valid, usable OAuth token is available."""
        creds = self._load_credentials()
        return creds is not None and creds.valid

    def _load_credentials(self) -> Any:
        """Load stored credentials and refresh if expired."""
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials

        if not self.token_file.exists():
            return None

        try:
            with open(self.token_file, encoding="utf-8") as f:
                token_data = json.load(f)
            creds = Credentials.from_authorized_user_info(token_data, CALENDAR_SCOPES)
        except Exception as e:
            logger.warning(f"Failed to read Google token file: {e}")
            return None

        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                self._save_credentials(creds)
            except Exception as e:
                logger.error(f"Failed to refresh Google OAuth token: {e}")
                return None

        return creds if creds and creds.valid else None

    def _save_credentials(self, creds: Any) -> None:
        """Save authorized credentials to disk securely."""
        self.token_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.token_file, "w", encoding="utf-8") as f:
            f.write(creds.to_json())

    def get_authorization_url(self) -> str:
        """Generate Google OAuth 2.0 consent URL for the business owner."""
        if not self.is_configured():
            raise ValueError(
                "GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be configured before authorizing."
            )

        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        flow = Flow.from_client_config(
            client_config,
            scopes=CALENDAR_SCOPES,
            redirect_uri=self.redirect_uri,
        )
        auth_url, _ = flow.authorization_url(
            access_type="offline",
            include_granted_scopes="true",
            prompt="consent",
        )
        return auth_url

    def exchange_code(self, code: str) -> bool:
        """Exchange authorization code for tokens and save to disk."""
        if not self.is_configured():
            return False

        from google_auth_oauthlib.flow import Flow

        client_config = {
            "web": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [self.redirect_uri],
            }
        }
        try:
            flow = Flow.from_client_config(
                client_config,
                scopes=CALENDAR_SCOPES,
                redirect_uri=self.redirect_uri,
            )
            flow.fetch_token(code=code)
            self._save_credentials(flow.credentials)
            self._service = None  # Reset cached API client
            logger.info("Google Calendar authorization successful.")
            return True
        except Exception as e:
            logger.error(f"Error exchanging OAuth code: {e}")
            return False

    def get_calendar_client(self) -> Any:
        """Build and cache the Google Calendar Resource client."""
        if self._service is not None:
            return self._service

        creds = self._load_credentials()
        if not creds:
            return None

        from googleapiclient.discovery import build

        self._service = build(
            "calendar", "v3", credentials=creds, cache_discovery=False
        )
        return self._service

    def check_calendar_slot(
        self,
        appointment_date: str,
        appointment_time: str,
        duration_minutes: int = 45,
    ) -> tuple[bool, str]:
        """Check if an appointment slot is free on Google Calendar."""
        service = self.get_calendar_client()
        if not service:
            # If calendar is not configured, we do not block local booking
            return True, "Calendar is not connected; skipping remote conflict check."

        tz = ZoneInfo(self.timezone_name)
        start_dt = datetime.strptime(
            f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        time_min = start_dt.isoformat()
        time_max = end_dt.isoformat()

        try:
            events_result = (
                service.events()
                .list(
                    calendarId=self.calendar_id,
                    timeMin=time_min,
                    timeMax=time_max,
                    singleEvents=True,
                    orderBy="startTime",
                )
                .execute()
            )
            items = events_result.get("items", [])
            # Filter out cancelled events
            active_events = [
                item for item in items if item.get("status") != "cancelled"
            ]
            if active_events:
                return (
                    False,
                    f"There is an existing calendar event between {appointment_time} and {end_dt.strftime('%H:%M')}.",
                )
            return True, "Calendar slot is available."
        except Exception as e:
            logger.error(f"Google Calendar conflict check failed: {e}")
            return (
                True,
                "Calendar check encountered an error; proceeding with local check.",
            )

    def create_event(
        self,
        *,
        customer_name: str,
        customer_phone: str,
        appointment_date: str,
        appointment_time: str,
        service_type: str,
        notes: str = "",
        duration_minutes: int = 45,
    ) -> tuple[bool, str]:
        """Create a new event on Google Calendar.

        Returns (success: bool, event_id_or_error: str).
        """
        service = self.get_calendar_client()
        if not service:
            return False, "Google Calendar is not authorized or token is missing."

        tz = ZoneInfo(self.timezone_name)
        start_dt = datetime.strptime(
            f"{appointment_date} {appointment_time}", "%Y-%m-%d %H:%M"
        ).replace(tzinfo=tz)
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event_body = {
            "summary": f"{BUSINESS_NAME}: {service_type} - {customer_name}",
            "description": f"Customer: {customer_name}\nPhone: {customer_phone}\nService: {service_type}\nNotes: {notes or 'None'}",
            "start": {
                "dateTime": start_dt.isoformat(),
                "timeZone": self.timezone_name,
            },
            "end": {
                "dateTime": end_dt.isoformat(),
                "timeZone": self.timezone_name,
            },
            "status": "confirmed",
        }

        try:
            created_event = (
                service.events()
                .insert(calendarId=self.calendar_id, body=event_body)
                .execute()
            )
            event_id = created_event.get("id")
            logger.info(f"Google Calendar event created successfully: {event_id}")
            return True, str(event_id)
        except Exception as e:
            logger.error(f"Failed to create Google Calendar event: {e}")
            return False, f"Calendar API error: {e}"

    def delete_event(self, event_id: str) -> bool:
        """Delete an event from Google Calendar."""
        service = self.get_calendar_client()
        if not service:
            return False

        try:
            service.events().delete(
                calendarId=self.calendar_id, eventId=event_id
            ).execute()
            logger.info(f"Deleted Google Calendar event: {event_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete Google Calendar event {event_id}: {e}")
            return False


# Singleton calendar service instance
_calendar_service: GoogleCalendarService | None = None


def get_calendar_service() -> GoogleCalendarService:
    """Return the shared GoogleCalendarService singleton."""
    global _calendar_service
    if _calendar_service is None:
        _calendar_service = GoogleCalendarService()
    return _calendar_service
