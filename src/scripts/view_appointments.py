"""CLI Script to view, inspect, and delete appointments in SQLite database."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

src_dir = Path(__file__).parent.parent
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from database.appointments_db import (  # noqa: E402
    delete_all_appointments,
    delete_appointment_record,
    get_appointment_by_id,
    list_appointments_by_business,
)


def display_appointments() -> None:
    print("=" * 75)
    print(" VoiceDesk AI — SQLite Appointments Database")
    print("=" * 75)

    appointments = list_appointments_by_business(limit=100)
    if not appointments:
        print("\nNo appointments found in database (data/appointments.db).\n")
        return

    print(f"\nFound {len(appointments)} appointment(s):\n")
    print(
        f"{'ID':<4} {'Customer':<18} {'Phone':<14} {'Date':<12} {'Time':<8} {'Status':<10} {'Service'}"
    )
    print("-" * 75)
    for apt in appointments:
        print(
            f"{apt['id']:<4} {apt['customer_name'][:17]:<18} {apt['customer_phone'][:13]:<14} "
            f"{apt['appointment_date']:<12} {apt['appointment_time']:<8} {apt['status']:<10} {apt['service_type']}"
        )
    print("-" * 75)
    print()


def cleanup_google_calendar_events() -> int:
    """Find and delete all VoiceDesk events from Google Calendar."""
    from services.calendar_service import get_calendar_service

    cs = get_calendar_service()
    if not cs.is_connected():
        print("Google Calendar is not connected; skipping calendar cleanup.")
        return 0

    client = cs.get_calendar_client()
    if not client:
        return 0

    try:
        res = client.events().list(calendarId=cs.calendar_id, q="VoiceDesk").execute()
        items = res.get("items", [])
        count = 0
        for item in items:
            if cs.delete_event(item["id"]):
                count += 1
        return count
    except Exception as e:
        print(f"Error querying Google Calendar: {e}")
        return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        description="View or delete appointments in VoiceDesk AI database."
    )
    parser.add_argument(
        "--delete",
        type=int,
        metavar="ID",
        help="Delete a specific appointment by ID (and its Google Calendar event)",
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete ALL appointments from SQLite and Google Calendar",
    )
    parser.add_argument(
        "--change-id",
        nargs=2,
        type=int,
        metavar=("OLD_ID", "NEW_ID"),
        help="Change an existing appointment ID to a new number (e.g. --change-id 2 1)",
    )
    parser.add_argument(
        "--reset-counter",
        type=int,
        metavar="NUM",
        help="Set the auto-increment counter to NUM (next new appointment will get NUM + 1)",
    )
    parser.add_argument(
        "--clear-calendar",
        action="store_true",
        help="Delete orphaned VoiceDesk events directly from Google Calendar",
    )

    args = parser.parse_args()

    if args.change_id:
        old_id, new_id = args.change_id
        import sqlite3

        from config import DATABASE_PATH

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE appointments SET id = ? WHERE id = ?;", (new_id, old_id)
                )
                if cursor.rowcount > 0:
                    cursor.execute(
                        "UPDATE sqlite_sequence SET seq = (SELECT COALESCE(MAX(id), 0) FROM appointments) WHERE name = 'appointments';"
                    )
                    conn.commit()
                    print(f"Updated: Appointment ID {old_id} is now ID {new_id}.\n")
                else:
                    print(f"Error: Appointment with ID {old_id} not found.\n")
        except Exception as e:
            print(f"Failed to update ID: {e}\n")
        display_appointments()
        return

    if args.reset_counter is not None:
        import sqlite3

        from config import DATABASE_PATH

        try:
            with sqlite3.connect(DATABASE_PATH) as conn:
                conn.execute(
                    "UPDATE sqlite_sequence SET seq = ? WHERE name = 'appointments';",
                    (args.reset_counter,),
                )
                conn.commit()
            print(
                f"Counter updated to {args.reset_counter}. Next appointment will be ID {args.reset_counter + 1}.\n"
            )
        except Exception as e:
            print(f"Failed to update counter: {e}\n")
        return

    if args.clear_calendar:
        deleted = cleanup_google_calendar_events()
        print(f"Cleaned up {deleted} VoiceDesk event(s) from Google Calendar.\n")
        return

    if args.delete is not None:
        apt = get_appointment_by_id(args.delete)
        if apt and apt.get("calendar_event_id"):
            try:
                from services.calendar_service import get_calendar_service

                cs = get_calendar_service()
                if cs.is_connected():
                    cs.delete_event(apt["calendar_event_id"])
                    print(
                        f"Deleted linked Google Calendar event: {apt['calendar_event_id']}"
                    )
            except Exception as e:
                print(f"Warning: Could not delete calendar event: {e}")

        deleted = delete_appointment_record(args.delete)
        if deleted:
            print(
                f"Appointment ID {args.delete} was successfully deleted from SQLite.\n"
            )
        else:
            print(f"Appointment ID {args.delete} not found.\n")
        display_appointments()
    elif args.clear:
        # Also clean up any linked Google Calendar events
        cal_count = cleanup_google_calendar_events()
        count = delete_all_appointments()
        print(f"Deleted {count} appointment(s) from SQLite.")
        if cal_count:
            print(f"Deleted {cal_count} synced event(s) from Google Calendar.")
        print("Table is now empty and ID sequence reset to 1.\n")
    else:
        display_appointments()
        print("Tips & Commands:")
        print("  Delete an appointment:     uv run python src/scripts/view_appointments.py --delete <ID>")
        print("  Change an appointment ID:  uv run python src/scripts/view_appointments.py --change-id <OLD_ID> <NEW_ID>")
        print("  Reset counter (start @ 1): uv run python src/scripts/view_appointments.py --reset-counter 0")
        print("  Wipe database & calendar:  uv run python src/scripts/view_appointments.py --clear\n")


if __name__ == "__main__":
    main()
