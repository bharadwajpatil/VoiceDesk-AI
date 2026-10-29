"""Unit and turn-level tests for VoiceDesk AI Voice Receptionist."""

from __future__ import annotations

import pytest
from livekit.agents import AgentSession

import config
from agent import Assistant


def test_config_validation() -> None:
    """Verify configuration loading and defaults."""
    missing = config.validate_config()
    assert isinstance(missing, list)
    assert config.BUSINESS_NAME == "VoiceDesk"
    assert config.STT_MODEL == "deepgram/nova-3"
    assert config.TTS_MODEL == "cartesia/sonic-3"
    assert config.STT_LANGUAGE in ("en", "en-IN")
    assert config.AUDIO_INPUT_SAMPLE_RATE == 16000
    assert config.AUDIO_ENABLE_AGC is True
    assert config.VAD_MIN_SILENCE_DURATION >= 0.5
    assert config.ENDPOINTING_MIN_DELAY >= 0.8


def test_receptionist_prompt_includes_speech_rules() -> None:
    """Verify that receptionist instructions include speech comprehension and anti-guessing rules."""
    from prompts.receptionist_prompt import get_receptionist_instructions

    prompt = get_receptionist_instructions()
    assert "Indian English" in prompt
    assert "NEVER GUESS" in prompt
    assert "repeat" in prompt.lower()


@pytest.mark.asyncio
async def test_receptionist_greeting_response() -> None:
    """Test that the assistant responds to a greeting appropriately."""
    async with AgentSession() as session:
        await session.start(Assistant())
        result = await session.run(user_input="Hello")
        event = result.expect.next_event()
        event.is_message(role="assistant")
        result.expect.no_more_events()


@pytest.mark.asyncio
async def test_receptionist_appointment_inquiry() -> None:
    """Test that the assistant responds to an appointment inquiry."""
    async with AgentSession() as session:
        await session.start(Assistant())
        result = await session.run(
            user_input="I would like to book an appointment tomorrow at 5 PM."
        )
        event = result.expect.next_event()
        try:
            event.is_message(role="assistant")
        except AssertionError:
            event.is_function_call()


@pytest.mark.asyncio
async def test_receptionist_faq_hours() -> None:
    """Test that the assistant answers questions about business hours."""
    async with AgentSession() as session:
        await session.start(Assistant())
        result = await session.run(user_input="What are your business hours?")
        event = result.expect.next_event()
        try:
            event.is_message(role="assistant")
        except AssertionError:
            event.is_function_call()
