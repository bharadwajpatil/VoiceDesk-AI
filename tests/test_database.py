"""Tests for SQLite appointment storage repository."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from database.appointments_db import (
    cancel_appointment_record,
    check_conflicting_appointment,
    create_appointment_record,
    get_appointment_by_id,
    init_db,
    list_appointments_by_business,
    update_appointment,
)


@pytest.fixture
def temp_db_path() -> Path:
    """Create a temporary database path for test isolation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir) / "test_appointments.db"


def test_init_db(temp_db_path: Path) -> None:
    """Test that init_db creates tables without errors."""
    init_db(temp_db_path)
    assert temp_db_path.exists()

    # Re-running init_db must preserve tables and not raise
    init_db(temp_db_path)


def test_create_and_get_appointment(temp_db_path: Path) -> None:
    """Test creating and retrieving an appointment record."""
    record = create_appointment_record(
        customer_name="Alice Smith",
        customer_phone="+15551234567",
        appointment_date="2026-10-15",
        appointment_time="14:00",
        service_type="Consultation",
        notes="First time customer",
        business_id="biz_1",
        status="pending",
        db_path=temp_db_path,
    )
    assert record["id"] is not None
    assert record["customer_name"] == "Alice Smith"
    assert record["customer_phone"] == "+15551234567"
    assert record["status"] == "pending"
    assert record["business_id"] == "biz_1"

    fetched = get_appointment_by_id(
        record["id"], business_id="biz_1", db_path=temp_db_path
    )
    assert fetched is not None
    assert fetched["id"] == record["id"]

    # Scoping test: query with wrong business_id should return None
    assert (
        get_appointment_by_id(
            record["id"], business_id="other_biz", db_path=temp_db_path
        )
        is None
    )


def test_list_appointments(temp_db_path: Path) -> None:
    """Test listing appointments with filtering."""
    create_appointment_record(
        customer_name="Bob",
        customer_phone="1234567890",
        appointment_date="2026-10-15",
        appointment_time="10:00",
        service_type="Consultation",
        status="pending",
        db_path=temp_db_path,
    )
    create_appointment_record(
        customer_name="Charlie",
        customer_phone="0987654321",
        appointment_date="2026-10-16",
        appointment_time="11:00",
        service_type="Review",
        status="confirmed",
        db_path=temp_db_path,
    )

    all_items = list_appointments_by_business(db_path=temp_db_path)
    assert len(all_items) == 2

    pending_items = list_appointments_by_business(
        status="pending", db_path=temp_db_path
    )
    assert len(pending_items) == 1
    assert pending_items[0]["customer_name"] == "Bob"

    date_items = list_appointments_by_business(date="2026-10-16", db_path=temp_db_path)
    assert len(date_items) == 1
    assert date_items[0]["customer_name"] == "Charlie"


def test_update_and_cancel_appointment(temp_db_path: Path) -> None:
    """Test updating and cancelling an appointment."""
    record = create_appointment_record(
        customer_name="Diana",
        customer_phone="5551112222",
        appointment_date="2026-10-20",
        appointment_time="15:30",
        service_type="Consultation",
        status="pending",
        db_path=temp_db_path,
    )

    # Update status to confirmed and assign calendar event ID
    updated = update_appointment(
        record["id"],
        {"status": "confirmed", "calendar_event_id": "cal_evt_123"},
        db_path=temp_db_path,
    )
    assert updated is not None
    assert updated["status"] == "confirmed"
    assert updated["calendar_event_id"] == "cal_evt_123"

    # Cancel appointment
    cancelled = cancel_appointment_record(record["id"], db_path=temp_db_path)
    assert cancelled is True

    record_after = get_appointment_by_id(record["id"], db_path=temp_db_path)
    assert record_after["status"] == "cancelled"


def test_check_conflicting_appointment(temp_db_path: Path) -> None:
    """Test conflict detection on identical dates and times."""
    create_appointment_record(
        customer_name="Eve",
        customer_phone="5553334444",
        appointment_date="2026-10-25",
        appointment_time="09:00",
        service_type="General",
        status="confirmed",
        db_path=temp_db_path,
    )

    # Same time should conflict
    assert (
        check_conflicting_appointment("2026-10-25", "09:00", db_path=temp_db_path)
        is True
    )

    # Different time should not conflict
    assert (
        check_conflicting_appointment("2026-10-25", "10:00", db_path=temp_db_path)
        is False
    )

    # Different date should not conflict
    assert (
        check_conflicting_appointment("2026-10-26", "09:00", db_path=temp_db_path)
        is False
    )
