"""Business Information Tools for VoiceDesk Receptionist.

Allows the AI voice receptionist to answer customer inquiries regarding
hours, location, services, and appointment policies from configuration.
"""

from __future__ import annotations

from livekit.agents import RunContext, function_tool

from config import (
    BUSINESS_HOURS,
    BUSINESS_LOCATION,
    BUSINESS_NAME,
    BUSINESS_POLICIES,
    BUSINESS_SERVICES,
)


@function_tool
async def get_business_hours(context: RunContext) -> str:
    """Return the official operating hours of the business.

    Use this tool whenever a caller asks when the business is open, closing times,
    or weekend availability.
    """
    return f"{BUSINESS_NAME} operating hours are: {BUSINESS_HOURS}"


@function_tool
async def get_business_location(context: RunContext) -> str:
    """Return the physical address and location details of the business.

    Use this tool when a caller asks where the business is located, directions,
    or address.
    """
    return f"{BUSINESS_NAME} is located at: {BUSINESS_LOCATION}"


@function_tool
async def get_services_offered(context: RunContext) -> str:
    """Return the list of services and appointments offered by the business.

    Use this tool when a caller asks what services are available or what they
    can book.
    """
    return f"Services offered at {BUSINESS_NAME} include: {BUSINESS_SERVICES}"


@function_tool
async def get_appointment_policies(context: RunContext) -> str:
    """Return cancellation, rescheduling, and arrival policies.

    Use this tool when a caller asks about cancellation policies, arrival times,
    or preparation requirements.
    """
    return f"Appointment policies: {BUSINESS_POLICIES}"
