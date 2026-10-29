"""Calendar and Appointment Booking Tools for VoiceDesk Receptionist.

Provides function tools for the AI agent to check slot availability,
create appointments after customer confirmation, and cancel appointments.
"""

from __future__ import annotations

from livekit.agents import RunContext, function_tool

from services.appointment_service import AppointmentService, ValidationError
from utils.logging import setup_logger

logger = setup_logger("voicedesk.tools.calendar")


@function_tool
async def check_slot_availability(
    context: RunContext,
    appointment_date: str,
    appointment_time: str,
) -> str:
    """Check if a specific appointment date and time slot is available.

    Args:
        appointment_date: Date in YYYY-MM-DD format (e.g. 2026-10-02).
        appointment_time: Time in 12-hour or 24-hour format (e.g. '5:00 PM' or '17:00').
    """
    logger.info(
        f"Checking slot availability for {appointment_date} at {appointment_time}"
    )
    service = AppointmentService()
    is_available, message = service.check_availability(
        appointment_date, appointment_time
    )
    if is_available:
        return (
            f"Slot {appointment_date} at {appointment_time} is available for booking."
        )
    return f"Slot {appointment_date} at {appointment_time} is NOT available: {message}"


@function_tool
async def book_appointment_tool(
    context: RunContext,
    customer_name: str,
    customer_phone: str,
    appointment_date: str,
    appointment_time: str,
    service_type: str,
    notes: str = "",
) -> str:
    """Book an appointment for the customer.

    IMPORTANT: Only call this tool AFTER you have collected all required information
    (name, phone number, date, time, service) and the customer has verbally CONFIRMED.

    Args:
        customer_name: The customer's full name.
        customer_phone: The customer's phone number.
        appointment_date: The appointment date in YYYY-MM-DD format.
        appointment_time: The appointment time (e.g. '17:00' or '5:00 PM').
        service_type: The type of service requested.
        notes: Any special customer notes or requests.
    """
    logger.info(
        f"Booking appointment for {customer_name}, date: {appointment_date}, time: {appointment_time}, service: {service_type}"
    )
    service = AppointmentService()
    try:
        booking = service.book_appointment(
            customer_name=customer_name,
            customer_phone=customer_phone,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            service_type=service_type,
            notes=notes,
            sync_calendar=True,
        )
        booking_id = booking["id"]
        status = booking["status"]

        if status == "confirmed":
            cal_id = booking.get("calendar_event_id", "")
            cal_str = f" (Calendar Event: {cal_id})" if cal_id else ""
            return (
                f"Success! Appointment ID {booking_id} is CONFIRMED on Google Calendar{cal_str} "
                f"for {customer_name} on {appointment_date} at {appointment_time} for {service_type}."
            )
        else:
            warning = booking.get("calendar_warning", "")
            warning_msg = f" Note: {warning}." if warning else ""
            return (
                f"Appointment ID {booking_id} has been saved with PENDING status "
                f"for {customer_name} on {appointment_date} at {appointment_time}.{warning_msg} "
                "Inform the customer their request has been received and is pending final confirmation."
            )
    except ValidationError as ve:
        logger.warning(f"Booking validation error: {ve}")
        return f"Cannot book appointment: {ve}"
    except Exception as e:
        logger.error(f"Unexpected booking error: {e}")
        return f"An unexpected error occurred while booking: {e}"


@function_tool
async def cancel_appointment_tool(
    context: RunContext,
    appointment_id: int,
) -> str:
    """Cancel an existing appointment by its numerical appointment ID.

    Args:
        appointment_id: The numerical ID of the appointment to cancel.
    """
    logger.info(f"Cancelling appointment ID {appointment_id}")
    service = AppointmentService()
    _success, message = service.cancel(appointment_id)
    return message
