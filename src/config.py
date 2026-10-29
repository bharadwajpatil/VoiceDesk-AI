"""VoiceDesk AI configuration module.

Centralizes environment variables, model choices, business parameters,
database configuration, and Google Calendar OAuth settings.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Search for .env.local first, then fall back to .env
ENV_PATHS = [
    Path(".env.local"),
    Path(__file__).parent.parent / ".env.local",
    Path(".env"),
    Path(__file__).parent.parent / ".env",
]

for env_path in ENV_PATHS:
    if env_path.is_file():
        load_dotenv(dotenv_path=env_path)
        break

BASE_DIR = Path(__file__).parent.parent

# LiveKit Server Settings
LIVEKIT_URL: str = os.getenv("LIVEKIT_URL", "")
LIVEKIT_API_KEY: str = os.getenv("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET: str = os.getenv("LIVEKIT_API_SECRET", "")

# AI Model Settings (LiveKit Cloud Inference Gateway)
LLM_MODEL: str = os.getenv("LLM_MODEL", "google/gemma-4-31b-it")
STT_MODEL: str = os.getenv("STT_MODEL", "deepgram/nova-3")
STT_LANGUAGE: str = os.getenv("STT_LANGUAGE", "en")
TTS_MODEL: str = os.getenv("TTS_MODEL", "cartesia/sonic-3")

# Business & Persona Configuration
BUSINESS_NAME: str = os.getenv("BUSINESS_NAME", "VoiceDesk")
BUSINESS_TYPE: str = os.getenv("BUSINESS_TYPE", "General Services & Appointments")
BUSINESS_HOURS: str = os.getenv(
    "BUSINESS_HOURS",
    "Monday through Saturday from 9:00 AM to 6:00 PM. Closed on Sundays.",
)
BUSINESS_LOCATION: str = os.getenv(
    "BUSINESS_LOCATION",
    "123 Innovation Boulevard, Suite 200",
)
BUSINESS_SERVICES: str = os.getenv(
    "BUSINESS_SERVICES",
    "General Consultation, Service Appointment, Follow-up Visit",
)
BUSINESS_POLICIES: str = os.getenv(
    "BUSINESS_POLICIES",
    "Please arrive five minutes prior to your scheduled time. Cancellations should be made at least two hours in advance.",
)
BUSINESS_TIMEZONE: str = os.getenv("BUSINESS_TIMEZONE", "UTC")
GREETING_MESSAGE: str = os.getenv(
    "GREETING_MESSAGE",
    f"Hello! Welcome to {BUSINESS_NAME}. How may I help you today?",
)

# Audio Configuration
AUDIO_INPUT_SAMPLE_RATE: int = int(os.getenv("AUDIO_INPUT_SAMPLE_RATE", "16000"))
AUDIO_SAMPLE_RATE: int = int(os.getenv("AUDIO_SAMPLE_RATE", "48000"))
AUDIO_CHANNELS: int = int(os.getenv("AUDIO_CHANNELS", "1"))
AUDIO_ENABLE_AGC: bool = os.getenv("AUDIO_ENABLE_AGC", "true").lower() in (
    "true",
    "1",
    "yes",
)

# Voice Activity Detection (VAD) Tuning
VAD_MIN_SPEECH_DURATION: float = float(os.getenv("VAD_MIN_SPEECH_DURATION", "0.08"))
VAD_MIN_SILENCE_DURATION: float = float(os.getenv("VAD_MIN_SILENCE_DURATION", "0.55"))
VAD_PREFIX_PADDING: float = float(os.getenv("VAD_PREFIX_PADDING", "0.5"))
VAD_ACTIVATION_THRESHOLD: float = float(os.getenv("VAD_ACTIVATION_THRESHOLD", "0.55"))

# Turn Handling & Endpointing Tuning (prevent premature cutoffs)
ENDPOINTING_MIN_DELAY: float = float(os.getenv("ENDPOINTING_MIN_DELAY", "0.85"))
ENDPOINTING_MAX_DELAY: float = float(os.getenv("ENDPOINTING_MAX_DELAY", "3.0"))

# Database Configuration (SQLite)
DATABASE_PATH: str = os.getenv(
    "DATABASE_PATH",
    str(BASE_DIR / "data" / "appointments.db"),
)

# Google Calendar OAuth 2.0 Configuration
GOOGLE_CLIENT_ID: str = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET: str = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI: str = os.getenv(
    "GOOGLE_REDIRECT_URI",
    "http://localhost:8080/",
)
GOOGLE_CALENDAR_ID: str = os.getenv("GOOGLE_CALENDAR_ID", "primary")
GOOGLE_TOKEN_FILE: str = os.getenv(
    "GOOGLE_TOKEN_FILE",
    str(BASE_DIR / "data" / "google_token.json"),
)


def validate_config() -> list[str]:
    """Validate that required environment variables are set.

    Returns a list of missing required variable names.
    """
    missing: list[str] = []
    if not LIVEKIT_URL:
        missing.append("LIVEKIT_URL")
    if not LIVEKIT_API_KEY:
        missing.append("LIVEKIT_API_KEY")
    if not LIVEKIT_API_SECRET:
        missing.append("LIVEKIT_API_SECRET")
    return missing
