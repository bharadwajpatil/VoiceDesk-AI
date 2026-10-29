"""VoiceDesk AI — AI Voice Receptionist.

Built with LiveKit Agents, Deepgram STT, Google Gemma LLM, and Cartesia TTS.
Features automated appointment booking, Google Calendar synchronization, and FAQ answering.
"""

from __future__ import annotations

from typing import Any

from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    STTContextOptions,
    TurnHandlingOptions,
    cli,
    inference,
    room_io,
)

import config
from prompts.receptionist_prompt import get_receptionist_instructions
from tools.business_info import (
    get_appointment_policies,
    get_business_hours,
    get_business_location,
    get_services_offered,
)
from tools.calendar import (
    book_appointment_tool,
    cancel_appointment_tool,
    check_slot_availability,
)
from utils.logging import setup_logger

logger = setup_logger("voicedesk.agent")


class Assistant(Agent):
    """The VoiceDesk Receptionist Agent equipped with business tools."""

    def __init__(self) -> None:
        super().__init__(
            llm=inference.LLM(model=config.LLM_MODEL),
            instructions=get_receptionist_instructions(),
            tools=[
                get_business_hours,
                get_business_location,
                get_services_offered,
                get_appointment_policies,
                check_slot_availability,
                book_appointment_tool,
                cancel_appointment_tool,
            ],
        )


server = AgentServer()


@server.rtc_session(agent_name="voicedesk-ai")
async def my_agent(ctx: JobContext) -> None:
    """Session entrypoint for each inbound voice connection."""
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }
    logger.info(f"Initiating VoiceDesk session in room: {ctx.room.name}")

    # Voice pipeline: Deepgram STT with smart formatting, Silero VAD, Cartesia Sonic-3 TTS, and TurnDetector
    session = AgentSession(
        stt=inference.STT(
            model=config.STT_MODEL,
            language=config.STT_LANGUAGE,
            extra_kwargs={
                "smart_format": True,
                "punctuate": True,
                "numerals": True,
                "interim_results": True,
            },
        ),
        vad=inference.VAD(
            model="silero",
            min_speech_duration=config.VAD_MIN_SPEECH_DURATION,
            min_silence_duration=config.VAD_MIN_SILENCE_DURATION,
            prefix_padding_duration=config.VAD_PREFIX_PADDING,
            activation_threshold=config.VAD_ACTIVATION_THRESHOLD,
        ),
        stt_context_options=STTContextOptions(
            keyterms=[
                config.BUSINESS_NAME,
                "appointment",
                "booking",
                "consultation",
                "schedule",
                "reschedule",
                "cancel",
                "receptionist",
                "tomorrow",
                "morning",
                "afternoon",
                "evening",
                "confirmed",
                "pending",
            ],
            keyterm_detection={"enabled": True},
        ),
        tts=inference.TTS(
            model=config.TTS_MODEL,
        ),
        turn_handling=TurnHandlingOptions(
            turn_detection=inference.TurnDetector(),
            endpointing={
                "min_delay": config.ENDPOINTING_MIN_DELAY,
                "max_delay": config.ENDPOINTING_MAX_DELAY,
            },
            interruption={
                "mode": "adaptive",
                "min_duration": 0.5,
                "min_words": 1,
                "resume_false_interruption": True,
            },
            preemptive_generation={"enabled": False},
        ),
    )

    # Attach speech recognition and conversation lifecycle loggers
    @session.on("user_input_transcribed")
    def _on_user_input_transcribed(ev: Any) -> None:
        transcript = getattr(ev, "transcript", "")
        if not transcript or not transcript.strip():
            return
        is_final = getattr(ev, "is_final", False)
        lang = getattr(ev, "language", None)
        if is_final:
            logger.info(
                f'🎙️ [STT Final Transcript] "{transcript.strip()}" (lang={lang})'
            )
        else:
            logger.debug(f'🎙️ [STT Interim] "{transcript.strip()}"')

    @session.on("conversation_item_added")
    def _on_conversation_item_added(ev: Any) -> None:
        item = getattr(ev, "item", None)
        if not item:
            return
        role = getattr(item, "role", None)
        text = getattr(item, "text_content", None) or getattr(item, "content", None)
        if not text or not str(text).strip():
            return
        if role == "user":
            logger.info(f'🧠 [LLM Input] "{str(text).strip()}"')
        elif role == "assistant":
            logger.info(f'🤖 [LLM Response] "{str(text).strip()}"')

    # Start the session and wire audio input/output
    await session.start(
        agent=Assistant(),
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_output=room_io.AudioOutputOptions(
                sample_rate=config.AUDIO_SAMPLE_RATE,
                num_channels=config.AUDIO_CHANNELS,
            ),
            audio_input=room_io.AudioInputOptions(
                sample_rate=config.AUDIO_INPUT_SAMPLE_RATE,
                num_channels=config.AUDIO_CHANNELS,
                auto_gain_control=config.AUDIO_ENABLE_AGC,
            ),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()
    logger.info("Connected to user room. Speaking opening greeting.")

    # Speak the opening receptionist greeting immediately upon connection
    await session.say(config.GREETING_MESSAGE, allow_interruptions=True)


if __name__ == "__main__":
    cli.run_app(server)
