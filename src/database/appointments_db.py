"""SQLite appointment storage repository for VoiceDesk AI.

Provides persistent, parameterized database operations for appointment records.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from config import DATABASE_PATH

# Valid statuses as defined in project requirements
ALLOWED_STATUSES = {"pending", "confirmed", "cancelled", "failed"}


def get_db_path(custom_path: str | Path | None = None) -> Path:
    """Return the resolved Path to the SQLite database, ensuring directory exists."""
    path_str = (
        str(custom_path) if custom_path else os.getenv("DATABASE_PATH", DATABASE_PATH)
    )
    path = Path(path_str)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def get_connection(db_path: str | Path | None = None) -> sqlite3.Connection:
    """Create and return a configured SQLite connection."""
    target_path = get_db_path(db_path)
    conn = sqlite3.connect(str(target_path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(db_path: str | Path | None = None) -> None:
    """Initialize the appointments table and required indexes.

    Preserves existing data using CREATE TABLE IF NOT EXISTS.
    """
    with get_connection(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                business_id TEXT NOT NULL DEFAULT 'default',
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                appointment_date TEXT NOT NULL,
                appointment_time TEXT NOT NULL,
                service_type TEXT NOT NULL,
                notes TEXT,
                status TEXT NOT NULL CHECK(status IN ('pending', 'confirmed', 'cancelled', 'failed')),
                calendar_event_id TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_appointments_business_status
            ON appointments (business_id, status);
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_appointments_date_time
            ON appointments (business_id, appointment_date, appointment_time);
            """
        )
        conn.commit()


def create_appointment_record(
    *,
    customer_name: str,
    customer_phone: str,
    appointment_date: str,
    appointment_time: str,
    service_type: str,
    notes: str = "",
    business_id: str = "default",
    status: str = "pending",
    calendar_event_id: str | None = None,
    db_path: str | Path | None = None,
) -> dict[str, Any]:
    """Insert a new appointment record using parameterized queries."""
    if status not in ALLOWED_STATUSES:
        raise ValueError(
            f"Invalid status '{status}'. Must be one of {ALLOWED_STATUSES}"
        )

    init_db(db_path)
    now_iso = datetime.now(timezone.utc).isoformat()

    query = """
        INSERT INTO appointments (
            business_id, customer_name, customer_phone,
            appointment_date, appointment_time, service_type,
            notes, status, calendar_event_id, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
    """
    params = (
        business_id,
        customer_name.strip(),
        customer_phone.strip(),
        appointment_date.strip(),
        appointment_time.strip(),
        service_type.strip(),
        notes.strip() if notes else None,
        status,
        calendar_event_id,
        now_iso,
        now_iso,
    )

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        new_id = cursor.lastrowid
        conn.commit()

    return get_appointment_by_id(new_id, business_id=business_id, db_path=db_path)  # type: ignore[return-value]


def get_appointment_by_id(
    appointment_id: int,
    business_id: str = "default",
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Retrieve an appointment by ID scoped to the business."""
    init_db(db_path)
    query = "SELECT * FROM appointments WHERE id = ? AND business_id = ?;"
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (appointment_id, business_id))
        row = cursor.fetchone()
        return dict(row) if row else None


def list_appointments_by_business(
    business_id: str = "default",
    status: str | None = None,
    date: str | None = None,
    limit: int = 50,
    offset: int = 0,
    db_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """List appointments for a business with optional status and date filters."""
    init_db(db_path)
    conditions = ["business_id = ?"]
    params: list[Any] = [business_id]

    if status:
        conditions.append("status = ?")
        params.append(status)
    if date:
        conditions.append("appointment_date = ?")
        params.append(date)

    params.extend([limit, offset])
    query = f"""
        SELECT * FROM appointments
        WHERE {" AND ".join(conditions)}
        ORDER BY appointment_date ASC, appointment_time ASC
        LIMIT ? OFFSET ?;
    """

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def update_appointment(
    appointment_id: int,
    updates: dict[str, Any],
    business_id: str = "default",
    db_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Update specific fields of an existing appointment."""
    init_db(db_path)
    allowed_fields = {
        "customer_name",
        "customer_phone",
        "appointment_date",
        "appointment_time",
        "service_type",
        "notes",
        "status",
        "calendar_event_id",
    }
    filtered_updates = {k: v for k, v in updates.items() if k in allowed_fields}
    if not filtered_updates:
        return get_appointment_by_id(
            appointment_id, business_id=business_id, db_path=db_path
        )

    if (
        "status" in filtered_updates
        and filtered_updates["status"] not in ALLOWED_STATUSES
    ):
        raise ValueError(
            f"Invalid status '{filtered_updates['status']}'. Must be one of {ALLOWED_STATUSES}"
        )

    filtered_updates["updated_at"] = datetime.now(timezone.utc).isoformat()

    set_clauses = [f"{col} = ?" for col in filtered_updates]
    params = list(filtered_updates.values())
    params.extend([appointment_id, business_id])

    query = f"""
        UPDATE appointments
        SET {", ".join(set_clauses)}
        WHERE id = ? AND business_id = ?;
    """

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()

    return get_appointment_by_id(
        appointment_id, business_id=business_id, db_path=db_path
    )


def cancel_appointment_record(
    appointment_id: int,
    business_id: str = "default",
    db_path: str | Path | None = None,
) -> bool:
    """Cancel an appointment record by setting status to 'cancelled'."""
    updated = update_appointment(
        appointment_id,
        {"status": "cancelled"},
        business_id=business_id,
        db_path=db_path,
    )
    return updated is not None and updated.get("status") == "cancelled"


def check_conflicting_appointment(
    appointment_date: str,
    appointment_time: str,
    business_id: str = "default",
    exclude_id: int | None = None,
    db_path: str | Path | None = None,
) -> bool:
    """Check if an active (pending/confirmed) appointment already exists at date and time."""
    init_db(db_path)
    query = """
        SELECT 1 FROM appointments
        WHERE business_id = ?
          AND appointment_date = ?
          AND appointment_time = ?
          AND status IN ('pending', 'confirmed')
    """
    params: list[Any] = [business_id, appointment_date, appointment_time]

    if exclude_id is not None:
        query += " AND id != ?"
        params.append(exclude_id)

    query += " LIMIT 1;"

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchone() is not None


def delete_appointment_record(
    appointment_id: int,
    business_id: str = "default",
    db_path: str | Path | None = None,
) -> bool:
    """Permanently delete an appointment record by ID from the appointments table."""
    init_db(db_path)
    query = "DELETE FROM appointments WHERE id = ? AND business_id = ?;"
    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, (appointment_id, business_id))
        conn.commit()
        return cursor.rowcount > 0


def delete_all_appointments(
    business_id: str | None = None,
    db_path: str | Path | None = None,
) -> int:
    """Permanently delete appointments (optionally scoped to a business_id)."""
    init_db(db_path)
    if business_id:
        query = "DELETE FROM appointments WHERE business_id = ?;"
        params: tuple[Any, ...] = (business_id,)
    else:
        query = "DELETE FROM appointments;"
        params = ()

    with get_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        # Reset the auto-increment counter when wiping the entire table
        if not business_id:
            conn.execute("DELETE FROM sqlite_sequence WHERE name = 'appointments';")
        conn.commit()
        return cursor.rowcount
