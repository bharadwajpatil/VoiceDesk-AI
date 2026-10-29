"""Tests for AppointmentService business logic and validation."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from services.appointment_service import (
    AppointmentService,
    ValidationError,
    normalize_date,
    normalize_phone_number,
    normalize_time,
)


@pytest.fixture
def service_with_temp_db() -> AppointmentService:
    """Provide an AppointmentService pointing to an isolated temp database."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_file = Path(tmpdir) / "test_service.db"
        yield AppointmentService(business_id="test_biz", db_path=db_file)


def test_phone_number_normalization() -> None:
    """Test valid and invalid phone numbers."""
    assert normalize_phone_number("+1 (555) 234-5678") == "+15552345678"
    assert normalize_phone_number("9876543210") == "9876543210"

    with pytest.raises(ValidationError):
        normalize_phone_number("123")  # too short


def test_time_normalization() -> None:
    """Test standardizing various time string inputs."""
    assert normalize_time("17:00") == "17:00"
    assert normalize_time("5:00 PM") == "17:00"
    assert normalize_time("5 PM") == "17:00"
    assert normalize_time("9:30 AM") == "09:30"
    assert normalize_time("12:00 PM") == "12:00"

    with pytest.raises(ValidationError):
        normalize_time("not-a-time")


def test_date_validation_and_past_dates() -> None:
    """Test ISO date parsing and past date rejection."""
    # Future date must succeed
    assert normalize_date("2030-01-01") == "2030-01-01"

    # Past date must raise ValidationError
    with pytest.raises(ValidationError, match="in the past"):
        normalize_date("2020-01-01")

    # Malformed date must raise ValidationError
    with pytest.raises(ValidationError, match="Invalid date format"):
        normalize_date("tomorrow")


def test_book_appointment_success(service_with_temp_db: AppointmentService) -> None:
    """Test booking an appointment with valid details."""
    booking = service_with_temp_db.book_appointment(
        customer_name="Frank Miller",
        customer_phone="555-444-3322",
        appointment_date="2026-11-01",
        appointment_time="14:00",
        service_type="Consultation",
        notes="Needs parking spot",
        sync_calendar=False,
    )
    assert booking["id"] is not None
    assert booking["status"] == "pending"
    assert booking["customer_name"] == "Frank Miller"
    assert booking["appointment_time"] == "14:00"


def test_book_appointment_missing_required_fields(
    service_with_temp_db: AppointmentService,
) -> None:
    """Test validation errors for empty fields."""
    with pytest.raises(ValidationError, match="Customer name"):
        service_with_temp_db.book_appointment(
            customer_name="",
            customer_phone="5551234567",
            appointment_date="2026-11-01",
            appointment_time="14:00",
            service_type="Consultation",
            sync_calendar=False,
        )

    with pytest.raises(ValidationError, match="Service type"):
        service_with_temp_db.book_appointment(
            customer_name="George",
            customer_phone="5551234567",
            appointment_date="2026-11-01",
            appointment_time="14:00",
            service_type="",
            sync_calendar=False,
        )


def test_book_duplicate_conflict(service_with_temp_db: AppointmentService) -> None:
    """Test that booking the same time slot raises a conflict error."""
    service_with_temp_db.book_appointment(
        customer_name="User One",
        customer_phone="5551112222",
        appointment_date="2026-11-05",
        appointment_time="10:00",
        service_type="Service A",
        sync_calendar=False,
    )

    with pytest.raises(ValidationError, match="already booked"):
        service_with_temp_db.book_appointment(
            customer_name="User Two",
            customer_phone="5559998888",
            appointment_date="2026-11-05",
            appointment_time="10:00",
            service_type="Service B",
            sync_calendar=False,
        )
