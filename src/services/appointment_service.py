"""Appointment Service for VoiceDesk AI.

Coordinates appointment validation, local SQLite persistence, conflict detection,
and Google Calendar synchronization.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

from config import BUSINESS_TIMEZONE
from database.appointments_db import (
    cancel_appointment_record,
    check_conflicting_appointment,
    create_appointment_record,
    get_appointment_by_id,
    list_appointments_by_business,
)


class ValidationError(Exception):
    """Raised when appointment input validation fails."""


def normalize_phone_number(phone: str) -> str:
    """Validate and clean phone numbers into digits and optional leading plus."""
    cleaned = re.sub(r"[^\d+]", "", phone.strip())
    # Minimum valid length check
    digits_only = re.sub(r"\D", "", cleaned)
    if len(digits_only) < 7:
        raise ValidationError("Phone number must have at least 7 digits.")
    return cleaned


def normalize_date(date_str: str, timezone_name: str = BUSINESS_TIMEZONE) -> str:
    """Validate date format (YYYY-MM-DD) and ensure it is not in the past."""
    date_str = date_str.strip()
    try:
        parsed_date = date.fromisoformat(date_str)
    except ValueError as e:
        raise ValidationError(
            f"Invalid date format '{date_str}'. Expected YYYY-MM-DD (e.g. 2026-10-02)."
        ) from e

    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo("UTC")

    today = datetime.now(tz).date()
    if parsed_date < today:
        raise ValidationError(
            f"Appointment date '{date_str}' is in the past. Today is {today.isoformat()}."
        )

    return parsed_date.isoformat()


def normalize_time(time_str: str) -> str:
    """Validate and normalize appointment time to HH:MM (24-hour format).

    Accepts '17:00', '5:00 PM', '5 PM', '09:30', etc.
    """
    raw = time_str.strip().upper()

    # Try standard 24-hr formats first: HH:MM, HH:MM:SS
    for fmt in ("%H:%M", "%H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt).time()
            return parsed.strftime("%H:%M")
        except ValueError:
            pass

    # Try 12-hr AM/PM formats
    for fmt in ("%I:%M %p", "%I:%M%p", "%I %p", "%I%p"):
        try:
            parsed = datetime.strptime(raw, fmt).time()
            return parsed.strftime("%H:%M")
        except ValueError:
            pass

    raise ValidationError(
        f"Invalid time format '{time_str}'. Expected formats like '17:00' or '5:00 PM'."
    )


class AppointmentService:
    """High-level service managing business appointments."""

    def __init__(
        self, business_id: str = "default", db_path: str | None = None
    ) -> None:
        self.business_id = business_id
        self.db_path = db_path

    def check_availability(
        self, appointment_date: str, appointment_time: str
    ) -> tuple[bool, str]:
        """Check if the requested date and time are available locally.

        Returns (is_available, message).
        """
        try:
            norm_date = normalize_date(appointment_date)
            norm_time = normalize_time(appointment_time)
        except ValidationError as e:
            return False, str(e)

        has_conflict = check_conflicting_appointment(
            appointment_date=norm_date,
            appointment_time=norm_time,
            business_id=self.business_id,
            db_path=self.db_path,
        )
        if has_conflict:
            return False, f"The slot on {norm_date} at {norm_time} is already booked."
        return True, f"The slot on {norm_date} at {norm_time} is available."

    def book_appointment(
        self,
        *,
        customer_name: str,
        customer_phone: str,
        appointment_date: str,
        appointment_time: str,
        service_type: str,
        notes: str = "",
        sync_calendar: bool = True,
    ) -> dict[str, Any]:
        """Validate, book, and optionally synchronize an appointment with Google Calendar."""
        if not customer_name or len(customer_name.strip()) < 2:
            raise ValidationError("Customer name must be at least 2 characters.")

        if not service_type or not service_type.strip():
            raise ValidationError("Service type is required.")

        norm_phone = normalize_phone_number(customer_phone)
        norm_date = normalize_date(appointment_date)
        norm_time = normalize_time(appointment_time)

        # Check local database conflicts
        is_free, msg = self.check_availability(norm_date, norm_time)
        if not is_free:
            raise ValidationError(msg)

        # In Phase 2, save initially as 'pending'
        status = "pending"
        calendar_event_id: str | None = None
        calendar_error: str | None = None

        # In Phase 3: Try Google Calendar synchronization if requested
        if sync_calendar:
            from services.calendar_service import get_calendar_service

            cal_service = get_calendar_service()
            if cal_service.is_connected():
                # Check for Google Calendar conflicts
                cal_free, cal_msg = cal_service.check_calendar_slot(
                    norm_date, norm_time
                )
                if not cal_free:
                    raise ValidationError(f"Google Calendar conflict: {cal_msg}")

                # Create Google Calendar event
                success, event_id_or_err = cal_service.create_event(
                    customer_name=customer_name.strip(),
                    customer_phone=norm_phone,
                    appointment_date=norm_date,
                    appointment_time=norm_time,
                    service_type=service_type.strip(),
                    notes=notes.strip(),
                )
                if success:
                    status = "confirmed"
                    calendar_event_id = event_id_or_err
                else:
                    calendar_error = event_id_or_err

        # Save to SQLite
        appointment = create_appointment_record(
            business_id=self.business_id,
            customer_name=customer_name.strip(),
            customer_phone=norm_phone,
            appointment_date=norm_date,
            appointment_time=norm_time,
            service_type=service_type.strip(),
            notes=notes.strip(),
            status=status,
            calendar_event_id=calendar_event_id,
            db_path=self.db_path,
        )

        if calendar_error:
            appointment["calendar_warning"] = calendar_error

        return appointment

    def cancel(self, appointment_id: int) -> tuple[bool, str]:
        """Cancel an appointment and sync cancellation with Google Calendar if linked."""
        record = get_appointment_by_id(
            appointment_id, business_id=self.business_id, db_path=self.db_path
        )
        if not record:
            return False, f"Appointment ID {appointment_id} not found."

        if record["status"] == "cancelled":
            return True, f"Appointment ID {appointment_id} is already cancelled."

        # Cancel in SQLite
        success = cancel_appointment_record(
            appointment_id, business_id=self.business_id, db_path=self.db_path
        )
        if not success:
            return False, f"Failed to cancel appointment ID {appointment_id}."

        # If connected to Google Calendar, cancel the remote event
        cal_event_id = record.get("calendar_event_id")
        if cal_event_id:
            from services.calendar_service import get_calendar_service

            cal_service = get_calendar_service()
            if cal_service.is_connected():
                cal_service.delete_event(cal_event_id)

        return True, f"Appointment ID {appointment_id} has been successfully cancelled."

    def get(self, appointment_id: int) -> dict[str, Any] | None:
        """Retrieve an appointment by ID."""
        return get_appointment_by_id(
            appointment_id, business_id=self.business_id, db_path=self.db_path
        )

    def list(
        self,
        status: str | None = None,
        date_filter: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List appointments for this business."""
        return list_appointments_by_business(
            business_id=self.business_id,
            status=status,
            date=date_filter,
            limit=limit,
            offset=offset,
            db_path=self.db_path,
        )
