"""Composition root: the only place that knows the concrete adapters.

It reads configuration, instantiates adapters (here just the HTTP brain client),
and wires them into the use case. Use cases see only ports, so swapping an
adapter is a change confined to this module.
"""

from __future__ import annotations

from application.use_cases.listen import ListenUseCase
from application.use_cases.speak_text import SpeakTextUseCase
from application.use_cases.text_turn import TextTurnUseCase
from config import Settings
from domain.models.conversation import ConversationSession
from infra.audio.sounddevice_player import SoundDevicePlayer
from infra.audio.sounddevice_recorder import SoundDeviceRecorder
from infra.brain.http_peruca_client import HttpPerucaClient
from infra.stt.whisper_transcriber import WhisperTranscriber
from infra.tts.piper_speaker import PiperSpeaker


def build_text_turn_use_case(settings: Settings) -> TextTurnUseCase:
    """Wire a :class:`TextTurnUseCase` from configuration."""
    brain_client = HttpPerucaClient(
        base_url=settings.peruca_api_url,
        timeout_seconds=settings.request_timeout_seconds,
    )
    session = ConversationSession(
        external_user_id=settings.external_user_id,
        chat_id=settings.chat_id,
    )
    return TextTurnUseCase(brain_client=brain_client, session=session)


def build_speak_text_use_case(settings: Settings) -> SpeakTextUseCase:
    """Wire a :class:`SpeakTextUseCase` from configuration.

    Loading the Piper voice here (once, at startup) keeps the heavy model off
    the per-turn critical path.
    """
    speaker = PiperSpeaker(
        model_path=settings.piper_voice_path,
        length_scale=settings.piper_length_scale,
    )
    speaker.warm_up()  # pay model loading at startup, not on the first utterance
    player = SoundDevicePlayer()
    return SpeakTextUseCase(speaker=speaker, player=player)


def build_listen_use_case(settings: Settings) -> ListenUseCase:
    """Wire a :class:`ListenUseCase` from configuration.

    Loads the Whisper model once (warm) at startup, off the per-turn path.
    """
    recorder = SoundDeviceRecorder(
        sample_rate=settings.capture_sample_rate,
        frame_size=settings.vad_frame_size,
        speech_threshold=settings.vad_speech_threshold,
        min_silence_ms=settings.vad_min_silence_ms,
        max_recording_ms=settings.vad_max_recording_ms,
        pre_roll_ms=settings.vad_pre_roll_ms,
        min_speech_ms=settings.vad_min_speech_ms,
    )
    transcriber = WhisperTranscriber(
        model_size=settings.whisper_model_size,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
        language=settings.stt_language,
        beam_size=settings.whisper_beam_size,
    )
    transcriber.warm_up()
    return ListenUseCase(recorder=recorder, transcriber=transcriber)
